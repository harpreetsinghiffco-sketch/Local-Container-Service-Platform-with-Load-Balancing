"""
Load Balancer for Local Container Service Platform
Supports multiple scheduling algorithms (Round Robin, Least Connections, Random, IP Hash)
and robust reverse proxying with automatic retry and telemetry.
"""

import time
import random
import hashlib
import threading
import urllib.request
import urllib.error
from urllib.parse import urljoin
from collections import defaultdict

class LoadBalancer:
    ALGORITHMS = ["round_robin", "least_connections", "random", "ip_hash"]

    def __init__(self, container_manager, algorithm="round_robin"):
        self.container_manager = container_manager
        self.algorithm = algorithm if algorithm in self.ALGORITHMS else "round_robin"
        self.lock = threading.Lock()
        self.rr_index = 0
        
        # Telemetry
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.per_instance_stats = defaultdict(lambda: {"requests": 0, "errors": 0, "total_latency_ms": 0})
        self.request_history = []  # Last 100 requests for live visualization

    def set_algorithm(self, algo_name):
        algo = algo_name.lower().replace("-", "_")
        if algo not in self.ALGORITHMS:
            raise ValueError(f"Unknown algorithm: {algo_name}. Supported: {self.ALGORITHMS}")
        with self.lock:
            self.algorithm = algo
        return self.algorithm

    def get_healthy_instances(self):
        instances = self.container_manager.list_instances()
        return [inst for inst in instances if inst.status == "RUNNING" and inst.health_status == "HEALTHY"]

    def select_instance(self, client_ip="127.0.0.1"):
        healthy_instances = self.get_healthy_instances()
        if not healthy_instances:
            return None

        with self.lock:
            if self.algorithm == "round_robin":
                selected = healthy_instances[self.rr_index % len(healthy_instances)]
                self.rr_index += 1
                return selected

            elif self.algorithm == "least_connections":
                # Select instance with minimum active connections
                return min(healthy_instances, key=lambda inst: inst.active_connections)

            elif self.algorithm == "random":
                return random.choice(healthy_instances)

            elif self.algorithm == "ip_hash":
                # Deterministic selection based on md5 hash of client ip
                hash_val = int(hashlib.md5(client_ip.encode('utf-8')).hexdigest(), 16)
                return healthy_instances[hash_val % len(healthy_instances)]

            # Default fallback
            return healthy_instances[0]

    def forward_request(self, method, path, headers=None, body=None, client_ip="127.0.0.1", max_retries=2):
        start_time = time.time()
        with self.lock:
            self.total_requests += 1

        retries = 0
        attempted_instances = set()

        while retries <= max_retries:
            instance = self.select_instance(client_ip=client_ip)
            if not instance or instance.id in attempted_instances:
                # Find any other healthy instance not yet attempted
                healthy = [i for i in self.get_healthy_instances() if i.id not in attempted_instances]
                if not healthy:
                    break
                instance = healthy[0]

            attempted_instances.add(instance.id)

            # Forward request to instance
            target_url = f"http://127.0.0.1:{instance.port}{path}"
            req_start = time.time()
            instance.active_connections += 1

            try:
                # Filter hop-by-hop headers
                clean_headers = {}
                if headers:
                    for k, v in headers.items():
                        if k.lower() not in ['host', 'connection', 'keep-alive', 'transfer-encoding']:
                            clean_headers[k] = v
                clean_headers['X-Forwarded-For'] = client_ip
                clean_headers['X-Load-Balancer-Algo'] = self.algorithm

                req = urllib.request.Request(
                    url=target_url,
                    data=body if method.upper() in ['POST', 'PUT', 'PATCH'] else None,
                    headers=clean_headers,
                    method=method.upper()
                )

                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    resp_status = resp.status
                    resp_headers = dict(resp.headers)
                    resp_body = resp.read()

                elapsed_ms = round((time.time() - req_start) * 1000, 2)
                instance.last_response_time_ms = elapsed_ms
                instance.requests_count += 1
                instance.active_connections = max(0, instance.active_connections - 1)

                with self.lock:
                    self.successful_requests += 1
                    stats = self.per_instance_stats[instance.id]
                    stats["requests"] += 1
                    stats["total_latency_ms"] += elapsed_ms
                    self._record_history(instance.id, method, path, resp_status, elapsed_ms, "SUCCESS")

                return {
                    "status_code": resp_status,
                    "headers": resp_headers,
                    "body": resp_body,
                    "served_by": instance.id,
                    "port": instance.port,
                    "latency_ms": elapsed_ms,
                    "algorithm": self.algorithm
                }

            except urllib.error.HTTPError as e:
                # Upstream HTTP error
                elapsed_ms = round((time.time() - req_start) * 1000, 2)
                instance.active_connections = max(0, instance.active_connections - 1)
                resp_body = e.read()
                
                # If 503 Service Unavailable, mark degraded and retry
                if e.code == 503 and retries < max_retries:
                    instance.health_status = "UNHEALTHY"
                    retries += 1
                    continue

                instance.requests_count += 1
                with self.lock:
                    self.successful_requests += 1  # Successfully proxied the response
                    self._record_history(instance.id, method, path, e.code, elapsed_ms, "HTTP_ERROR")

                return {
                    "status_code": e.code,
                    "headers": dict(e.headers),
                    "body": resp_body,
                    "served_by": instance.id,
                    "port": instance.port,
                    "latency_ms": elapsed_ms,
                    "algorithm": self.algorithm
                }

            except Exception as e:
                # Connection refused or timeout
                instance.active_connections = max(0, instance.active_connections - 1)
                instance.consecutive_failures += 1
                if instance.consecutive_failures >= 2:
                    instance.health_status = "UNHEALTHY"
                retries += 1

        # All retries exhausted or no instances available
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        with self.lock:
            self.failed_requests += 1
            self._record_history("NONE", method, path, 502, elapsed_ms, "ALL_BACKENDS_UNAVAILABLE")

        return {
            "status_code": 502,
            "headers": {"Content-Type": "application/json"},
            "body": b'{"error": "Bad Gateway", "message": "No healthy backend instances available"}',
            "served_by": None,
            "port": None,
            "latency_ms": elapsed_ms,
            "algorithm": self.algorithm
        }

    def _record_history(self, instance_id, method, path, status_code, latency_ms, status_label):
        self.request_history.insert(0, {
            "timestamp": time.strftime("%H:%M:%S"),
            "instance_id": instance_id,
            "method": method,
            "path": path,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "status": status_label
        })
        if len(self.request_history) > 50:
            self.request_history.pop()

    def get_stats(self):
        with self.lock:
            healthy = len(self.get_healthy_instances())
            total = len(self.container_manager.list_instances())
            
            distribution = {}
            for inst in self.container_manager.list_instances():
                stat = self.per_instance_stats[inst.id]
                avg_lat = round(stat["total_latency_ms"] / stat["requests"], 2) if stat["requests"] > 0 else 0
                distribution[inst.id] = {
                    "port": inst.port,
                    "requests": stat["requests"],
                    "avg_latency_ms": avg_lat,
                    "active_connections": inst.active_connections,
                    "health_status": inst.health_status
                }

            return {
                "algorithm": self.algorithm,
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "total_instances": total,
                "healthy_instances": healthy,
                "distribution": distribution,
                "recent_history": list(self.request_history[:15])
            }
