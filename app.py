#!/usr/bin/env python3
"""
Main Application Server for Local Container Service Platform with Load Balancing
Integrates:
- Control Plane REST API
- Reverse Proxy Load Balancer Gateway
- Interactive Web Dashboard
- Automated Health Checker & Dynamic Auto-Scaler
"""

import os
import sys
import json
import time
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from core.storage import Storage
from core.container_manager import ContainerManager
from core.load_balancer import LoadBalancer
from core.health_checker import HealthChecker
from core.auto_scaler import AutoScaler

# Global Platform Singletons
storage = Storage()
container_mgr = ContainerManager(storage=storage)
load_balancer = LoadBalancer(container_manager=container_mgr, algorithm="round_robin")
health_checker = HealthChecker(container_manager=container_mgr, storage=storage, interval_seconds=3)
auto_scaler = AutoScaler(container_manager=container_mgr, load_balancer=load_balancer, storage=storage)

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")

class PlatformHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress routine log clutter
        pass

    def _send_json(self, status_code, data):
        response_bytes = json.dumps(data, indent=2).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(response_bytes)

    def _serve_file(self, file_path, content_type):
        if not os.path.isfile(file_path):
            self._send_json(404, {"error": "File Not Found"})
            return
        with open(file_path, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # 1. Reverse Proxy / Gateway routes (/service/* or /proxy/*)
        if path.startswith("/service") or path.startswith("/proxy"):
            subpath = path.replace("/service", "", 1).replace("/proxy", "", 1) or "/"
            result = load_balancer.forward_request(
                method="GET",
                path=subpath,
                headers=dict(self.headers),
                client_ip=self.client_address[0]
            )
            self.send_response(result["status_code"])
            for k, v in result["headers"].items():
                if k.lower() not in ['transfer-encoding']:
                    self.send_header(k, v)
            self.send_header('X-Served-By-Container', str(result["served_by"]))
            self.send_header('X-LB-Algorithm', result["algorithm"])
            self.end_headers()
            self.wfile.write(result["body"])
            return

        # 2. Control Plane REST API routes
        if path == "/api/status":
            instances = [i.to_dict() for i in container_mgr.list_instances()]
            lb_stats = load_balancer.get_stats()
            hc_stats = health_checker.get_status()
            as_stats = auto_scaler.get_status()
            self._send_json(200, {
                "platform": "Local Container Service Platform with Load Balancing",
                "timestamp": time.time(),
                "instances": instances,
                "load_balancer": lb_stats,
                "health_checker": hc_stats,
                "auto_scaler": as_stats
            })
            return

        elif path == "/api/logs":
            logs = storage.get_audit_logs(limit=40)
            self._send_json(200, {"logs": logs})
            return

        elif path == "/api/health/check-now":
            health_checker.check_all()
            self._send_json(200, {"message": "Health check triggered", "status": health_checker.get_status()})
            return

        # 3. Static Web Dashboard Files
        if path == "/" or path == "/index.html":
            self._serve_file(os.path.join(WEB_DIR, "index.html"), "text/html; charset=utf-8")
        elif path == "/static/styles.css":
            self._serve_file(os.path.join(WEB_DIR, "static", "styles.css"), "text/css")
        elif path == "/static/app.js":
            self._serve_file(os.path.join(WEB_DIR, "static", "app.js"), "application/javascript")
        else:
            self._send_json(404, {"error": "Endpoint Not Found", "path": path})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get('Content-Length', 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b""
        
        try:
            payload = json.loads(body_bytes.decode('utf-8')) if body_bytes else {}
        except Exception:
            payload = {}

        # 1. Reverse Proxy Gateway for POST
        if path.startswith("/service") or path.startswith("/proxy"):
            subpath = path.replace("/service", "", 1).replace("/proxy", "", 1) or "/"
            result = load_balancer.forward_request(
                method="POST",
                path=subpath,
                headers=dict(self.headers),
                body=body_bytes,
                client_ip=self.client_address[0]
            )
            self.send_response(result["status_code"])
            for k, v in result["headers"].items():
                if k.lower() not in ['transfer-encoding']:
                    self.send_header(k, v)
            self.send_header('X-Served-By-Container', str(result["served_by"]))
            self.send_header('X-LB-Algorithm', result["algorithm"])
            self.end_headers()
            self.wfile.write(result["body"])
            return

        # 2. Control Plane Actions
        if path == "/api/containers/deploy":
            try:
                name = payload.get("name", "dummy-service")
                port = payload.get("port")
                driver = payload.get("driver", "process")
                instance = container_mgr.create_and_start(port=port, name=name, driver=driver)
                # Quick health check update
                time.sleep(0.2)
                health_checker._check_instance(instance)
                self._send_json(201, {"message": "Container deployed successfully", "container": instance.to_dict()})
            except Exception as e:
                self._send_json(400, {"error": str(e)})

        elif path.startswith("/api/containers/") and path.endswith("/stop"):
            cntr_id = path.split("/")[3]
            try:
                inst = container_mgr.stop(cntr_id)
                self._send_json(200, {"message": f"Container {cntr_id} stopped", "container": inst.to_dict()})
            except Exception as e:
                self._send_json(404, {"error": str(e)})

        elif path.startswith("/api/containers/") and path.endswith("/start"):
            cntr_id = path.split("/")[3]
            try:
                inst = container_mgr.start(cntr_id)
                time.sleep(0.2)
                health_checker._check_instance(inst)
                self._send_json(200, {"message": f"Container {cntr_id} started", "container": inst.to_dict()})
            except Exception as e:
                self._send_json(404, {"error": str(e)})

        elif path.startswith("/api/containers/") and path.endswith("/restart"):
            cntr_id = path.split("/")[3]
            try:
                inst = container_mgr.restart(cntr_id)
                time.sleep(0.2)
                health_checker._check_instance(inst)
                self._send_json(200, {"message": f"Container {cntr_id} restarted", "container": inst.to_dict()})
            except Exception as e:
                self._send_json(404, {"error": str(e)})

        elif path.startswith("/api/containers/") and path.endswith("/simulate/fail"):
            cntr_id = path.split("/")[3]
            inst = container_mgr.get_instance(cntr_id)
            if not inst or inst.status != "RUNNING":
                self._send_json(404, {"error": "Instance not found or not running"})
                return
            import urllib.request
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{inst.port}/simulate/fail", data=b'{"reason": "Injected hardware breakdown"}', method="POST")
                urllib.request.urlopen(req, timeout=1.0)
                health_checker._check_instance(inst)
                self._send_json(200, {"message": f"Failure simulated on {cntr_id}", "container": inst.to_dict()})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path.startswith("/api/containers/") and path.endswith("/simulate/recover"):
            cntr_id = path.split("/")[3]
            inst = container_mgr.get_instance(cntr_id)
            if not inst or inst.status != "RUNNING":
                self._send_json(404, {"error": "Instance not found or not running"})
                return
            import urllib.request
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{inst.port}/simulate/recover", data=b'{}', method="POST")
                urllib.request.urlopen(req, timeout=1.0)
                health_checker._check_instance(inst)
                self._send_json(200, {"message": f"Recovery simulated on {cntr_id}", "container": inst.to_dict()})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path == "/api/loadbalancer/algorithm":
            algo = payload.get("algorithm", "round_robin")
            try:
                active = load_balancer.set_algorithm(algo)
                storage.log_event("ALGORITHM_CHANGED", f"Load balancing algorithm changed to {active}")
                self._send_json(200, {"message": "Algorithm updated", "algorithm": active})
            except Exception as e:
                self._send_json(400, {"error": str(e)})

        elif path == "/api/autoscaler/config":
            auto_scaler.set_config(
                enabled=payload.get("enabled"),
                min_inst=payload.get("min_instances"),
                max_inst=payload.get("max_instances"),
                target_rps=payload.get("target_rps")
            )
            self._send_json(200, {"message": "AutoScaler configuration updated", "config": auto_scaler.get_status()})

        elif path == "/api/traffic/burst":
            count = int(payload.get("count", 10))
            results = []
            for i in range(min(count, 50)):
                res = load_balancer.forward_request("GET", "/api/data", client_ip="127.0.0.1")
                results.append({
                    "req_num": i + 1,
                    "served_by": res["served_by"],
                    "port": res["port"],
                    "latency_ms": res["latency_ms"],
                    "status_code": res["status_code"]
                })
            self._send_json(200, {
                "message": f"Executed traffic burst of {len(results)} requests",
                "results": results,
                "stats": load_balancer.get_stats()
            })
        else:
            self._send_json(404, {"error": "Not Found"})

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/containers/"):
            cntr_id = path.split("/")[3]
            try:
                container_mgr.remove(cntr_id)
                self._send_json(200, {"message": f"Container {cntr_id} removed"})
            except Exception as e:
                self._send_json(400, {"error": str(e)})
        else:
            self._send_json(404, {"error": "Not Found"})


def initialize_platform(initial_instances=3):
    print("=" * 65)
    print(" 🚀 STARTING LOCAL CONTAINER SERVICE PLATFORM WITH LOAD BALANCING")
    print("=" * 65)
    
    # Pre-deploy default healthy instances
    print(f"📦 Deploying initial pool of {initial_instances} container instances...")
    for i in range(initial_instances):
        try:
            inst = container_mgr.create_and_start()
            print(f"   [+] Container '{inst.id}' active on http://127.0.0.1:{inst.port}")
        except Exception as e:
            print(f"   [-] Failed to deploy instance {i}: {e}")

    # Start Daemons
    health_checker.start()
    print("🩺 Health Checker daemon started (interval: 3s).")

    auto_scaler.start()
    print("📈 Dynamic Auto-Scaler daemon started.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Container Service Platform with Load Balancing")
    parser.add_argument("--host", default="0.0.0.0", help="Binding host")
    parser.add_argument("--port", type=int, default=8000, help="Control Plane & Gateway Port")
    parser.add_argument("--instances", type=int, default=3, help="Initial instances count")
    args = parser.parse_args()

    initialize_platform(initial_instances=args.instances)

    server = ThreadingHTTPServer((args.host, args.port), PlatformHTTPHandler)
    print("\n" + "=" * 65)
    print(f"✨ Web Control Dashboard : http://localhost:{args.port}/")
    print(f"🔀 Load Balancer Gateway  : http://localhost:{args.port}/service/")
    print(f"📊 Platform Health & API : http://localhost:{args.port}/api/status")
    print("=" * 65 + "\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down platform...")
    finally:
        health_checker.stop()
        auto_scaler.stop()
        container_mgr.cleanup_all()
        server.server_close()
        print("✅ Clean shutdown completed.")


if __name__ == "__main__":
    main()
