#!/usr/bin/env python3
"""
Dummy Microservice for Container Service Platform
Simulates a containerized backend microservice with health checking,
latency simulation, failure injection, and telemetry metrics.
"""

import os
import sys
import time
import json
import socket
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone

class DummyServiceHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Clean logging format with timestamp
        sys.stdout.write(f"[{datetime.now().strftime('%H:%M:%S')}] [{self.server.instance_id}] {format % args}\n")
        sys.stdout.flush()

    def _send_json(self, status_code, data):
        response_bytes = json.dumps(data, indent=2).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.send_header('X-Container-Id', self.server.instance_id)
        self.send_header('X-Container-Port', str(self.server.port))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Simulate injected latency if configured
        if self.server.simulated_latency > 0:
            time.sleep(self.server.simulated_latency)

        if path == "/health":
            self.handle_health()
        elif path == "/metrics":
            self.handle_metrics()
        elif path == "/" or path == "/api" or path.startswith("/api/"):
            self.handle_service_request(path)
        else:
            self._send_json(404, {
                "error": "Not Found",
                "instance_id": self.server.instance_id,
                "requested_path": path
            })

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""
        
        try:
            payload = json.loads(body.decode('utf-8')) if body else {}
        except Exception:
            payload = {}

        if path == "/simulate/fail":
            self.server.is_healthy = False
            self.server.failure_reason = payload.get("reason", "Simulated system failure")
            self._send_json(200, {
                "status": "Failure simulated",
                "instance_id": self.server.instance_id,
                "is_healthy": self.server.is_healthy,
                "reason": self.server.failure_reason
            })
        elif path == "/simulate/recover":
            self.server.is_healthy = True
            self.server.failure_reason = ""
            self._send_json(200, {
                "status": "Service recovered",
                "instance_id": self.server.instance_id,
                "is_healthy": self.server.is_healthy
            })
        elif path == "/simulate/latency":
            seconds = float(payload.get("latency_seconds", 1.0))
            self.server.simulated_latency = max(0.0, seconds)
            self._send_json(200, {
                "status": "Simulated latency updated",
                "instance_id": self.server.instance_id,
                "latency_seconds": self.server.simulated_latency
            })
        else:
            # Regular POST handling on dummy service
            self.handle_service_request(path, method="POST", payload=payload)

    def handle_health(self):
        uptime = round(time.time() - self.server.start_time, 2)
        if self.server.is_healthy:
            self._send_json(200, {
                "status": "UP",
                "instance_id": self.server.instance_id,
                "port": self.server.port,
                "uptime_seconds": uptime,
                "requests_handled": self.server.request_count,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        else:
            self._send_json(503, {
                "status": "DOWN",
                "instance_id": self.server.instance_id,
                "port": self.server.port,
                "uptime_seconds": uptime,
                "reason": self.server.failure_reason or "Instance unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

    def handle_metrics(self):
        uptime = round(time.time() - self.server.start_time, 2)
        self._send_json(200, {
            "instance_id": self.server.instance_id,
            "port": self.server.port,
            "uptime_seconds": uptime,
            "requests_handled": self.server.request_count,
            "is_healthy": self.server.is_healthy,
            "simulated_latency": self.server.simulated_latency,
            "pid": os.getpid()
        })

    def handle_service_request(self, path, method="GET", payload=None):
        with self.server.lock:
            self.server.request_count += 1
            current_count = self.server.request_count

        uptime = round(time.time() - self.server.start_time, 2)
        self._send_json(200, {
            "status": "SUCCESS",
            "message": f"Processed by Dummy Service Container [{self.server.instance_id}]",
            "container": {
                "id": self.server.instance_id,
                "name": self.server.service_name,
                "port": self.server.port,
                "pid": os.getpid(),
                "uptime_seconds": uptime
            },
            "request_info": {
                "method": method,
                "path": path,
                "request_number": current_count,
                "payload": payload or {}
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


class DummyServiceServer(HTTPServer):
    def __init__(self, host, port, instance_id, service_name):
        import threading
        self.instance_id = instance_id
        self.service_name = service_name
        self.port = port
        self.start_time = time.time()
        self.request_count = 0
        self.is_healthy = True
        self.failure_reason = ""
        self.simulated_latency = 0.0
        self.lock = threading.Lock()
        super().__init__((host, port), DummyServiceHandler)


def run_service():
    parser = argparse.ArgumentParser(description="Run Dummy Container Microservice")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=9001, help="Port to listen on")
    parser.add_argument("--id", default="srv-default", help="Instance ID")
    parser.add_argument("--name", default="dummy-api-service", help="Service name")
    parser.add_argument("--latency", type=float, default=0.0, help="Initial artificial latency")
    args = parser.parse_args()

    server = DummyServiceServer(args.host, args.port, args.id, args.name)
    server.simulated_latency = args.latency
    print(f"🚀 Dummy Service '{args.name}' [{args.id}] listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n🛑 Dummy Service [{args.id}] shutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_service()
