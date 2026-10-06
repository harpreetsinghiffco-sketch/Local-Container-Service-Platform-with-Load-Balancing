#!/usr/bin/env python3
"""
CLI Management Tool for Local Container Service Platform
Interact with the running platform via terminal.
"""

import sys
import argparse
import urllib.request
import urllib.error
import json

BASE_URL = "http://127.0.0.1:8000"

def _request(method, endpoint, payload=None):
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode('utf-8') if payload else None
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode('utf-8'))
            print(f"❌ Error ({e.code}): {err.get('error', e.reason)}")
        except Exception:
            print(f"❌ HTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except urllib.error.URLError:
        print("❌ Cannot connect to platform gateway at http://127.0.0.1:8000. Is 'python3 app.py' running?")
        sys.exit(1)

def cmd_status(args):
    data = _request("GET", "/api/status")
    lb = data["load_balancer"]
    instances = data["instances"]
    
    print("\n" + "=" * 60)
    print(" 🚀 PLATFORM STATUS OVERVIEW")
    print("=" * 60)
    print(f"Algorithm         : {lb['algorithm']}")
    print(f"Total Requests    : {lb['total_requests']} (Success: {lb['successful_requests']}, Errors: {lb['failed_requests']})")
    print(f"Cluster Instances : {len(instances)} total, {lb['healthy_instances']} healthy")
    print("-" * 60)
    print(f"{'CONTAINER ID':<16} {'PORT':<8} {'DRIVER':<10} {'STATUS':<12} {'HEALTH':<10} {'REQUESTS'}")
    print("-" * 60)
    for inst in instances:
        print(f"{inst['id']:<16} {inst['port']:<8} {inst['driver']:<10} {inst['status']:<12} {inst['health_status']:<10} {inst['requests_count']}")
    print("=" * 60 + "\n")

def cmd_deploy(args):
    payload = {"name": args.name}
    if args.port:
        payload["port"] = args.port
    res = _request("POST", "/api/containers/deploy", payload)
    print(f"✅ Deployed: {res['container']['id']} on port {res['container']['port']}")

def cmd_stop(args):
    res = _request("POST", f"/api/containers/{args.id}/stop")
    print(f"🛑 Stopped container: {args.id}")

def cmd_start(args):
    res = _request("POST", f"/api/containers/{args.id}/start")
    print(f"▶ Started container: {args.id}")

def cmd_remove(args):
    res = _request("DELETE", f"/api/containers/{args.id}")
    print(f"🗑 Removed container: {args.id}")

def cmd_algo(args):
    res = _request("POST", "/api/loadbalancer/algorithm", {"algorithm": args.algorithm})
    print(f"🔀 Load Balancer algorithm set to: {res['algorithm']}")

def cmd_benchmark(args):
    print(f"⚡ Firing benchmark of {args.requests} requests through Load Balancer Gateway...")
    res = _request("POST", "/api/traffic/burst", {"count": args.requests})
    stats = res["stats"]
    print(f"✅ Completed {len(res['results'])} requests.")
    print("\nPer-Container Request Distribution:")
    for cid, dist in stats.get("distribution", {}).items():
        print(f"  • {cid:<14} (: {dist['port']}): {dist['requests']} reqs, avg latency: {dist['avg_latency_ms']}ms")
    print()

def main():
    parser = argparse.ArgumentParser(description="Container Service Platform CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Get platform & cluster status")
    p_status.set_defaults(func=cmd_status)

    # deploy
    p_deploy = subparsers.add_parser("deploy", help="Deploy new container instance")
    p_deploy.add_argument("--name", default="dummy-service", help="Container name")
    p_deploy.add_argument("--port", type=int, help="Optional port")
    p_deploy.set_defaults(func=cmd_deploy)

    # stop
    p_stop = subparsers.add_parser("stop", help="Stop container instance")
    p_stop.add_argument("id", help="Container ID")
    p_stop.set_defaults(func=cmd_stop)

    # start
    p_start = subparsers.add_parser("start", help="Start container instance")
    p_start.add_argument("id", help="Container ID")
    p_start.set_defaults(func=cmd_start)

    # rm
    p_rm = subparsers.add_parser("rm", help="Remove container instance")
    p_rm.add_argument("id", help="Container ID")
    p_rm.set_defaults(func=cmd_remove)

    # algo
    p_algo = subparsers.add_parser("algo", help="Change Load Balancing Algorithm")
    p_algo.add_argument("algorithm", choices=["round_robin", "least_connections", "random", "ip_hash"])
    p_algo.set_defaults(func=cmd_algo)

    # benchmark
    p_bench = subparsers.add_parser("benchmark", help="Execute traffic benchmark")
    p_bench.add_argument("--requests", type=int, default=20, help="Number of requests")
    p_bench.set_defaults(func=cmd_benchmark)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
