"""
Health Checker for Local Container Service Platform
Continuously checks the health of all registered container instances,
updates their state, and notifies storage/load-balancer on state transitions.
"""

import time
import threading
import urllib.request
import urllib.error
import json
from datetime import datetime, timezone

class HealthChecker:
    def __init__(self, container_manager, storage=None, interval_seconds=3, failure_threshold=2, success_threshold=2):
        self.container_manager = container_manager
        self.storage = storage
        self.interval = interval_seconds
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.last_check_timestamp = None
        self.check_results = {}

    def start(self):
        with self.lock:
            if self.running:
                return
            self.running = True
            self.thread = threading.Thread(target=self._check_loop, daemon=True, name="HealthCheckerThread")
            self.thread.start()

    def stop(self):
        with self.lock:
            self.running = False

    def _check_loop(self):
        while self.running:
            self.check_all()
            time.sleep(self.interval)

    def check_all(self):
        instances = self.container_manager.list_instances()
        self.last_check_timestamp = datetime.now(timezone.utc).isoformat()
        
        for instance in instances:
            if instance.status != "RUNNING":
                continue
            self._check_instance(instance)

    def _check_instance(self, instance):
        url = f"http://127.0.0.1:{instance.port}/health"
        is_healthy = False
        error_msg = ""
        check_start = time.time()

        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    if data.get("status") == "UP":
                        is_healthy = True
                else:
                    error_msg = f"HTTP {resp.status}"
        except urllib.error.HTTPError as e:
            error_msg = f"HTTP {e.code}"
        except Exception as e:
            error_msg = str(e)

        latency_ms = round((time.time() - check_start) * 1000, 2)

        # Update state transitions
        previous_health = instance.health_status
        if is_healthy:
            instance.consecutive_successes += 1
            instance.consecutive_failures = 0
            if instance.consecutive_successes >= self.success_threshold:
                instance.health_status = "HEALTHY"
                if previous_health != "HEALTHY":
                    if self.storage:
                        self.storage.log_event("HEALTH_RECOVERED", f"Container {instance.id} recovered and returned to active pool", {"port": instance.port})
                        self.storage.save_instance(instance.to_dict())
        else:
            instance.consecutive_failures += 1
            instance.consecutive_successes = 0
            if instance.consecutive_failures >= self.failure_threshold:
                instance.health_status = "UNHEALTHY"
                if previous_health == "HEALTHY":
                    if self.storage:
                        self.storage.log_event("HEALTH_FAILED", f"Container {instance.id} failed health checks: {error_msg}. Removed from pool.", {"port": instance.port})
                        self.storage.save_instance(instance.to_dict())

        with self.lock:
            self.check_results[instance.id] = {
                "instance_id": instance.id,
                "port": instance.port,
                "is_healthy": is_healthy,
                "health_status": instance.health_status,
                "latency_ms": latency_ms,
                "consecutive_failures": instance.consecutive_failures,
                "consecutive_successes": instance.consecutive_successes,
                "error": error_msg,
                "checked_at": self.last_check_timestamp
            }

    def get_status(self):
        with self.lock:
            return {
                "running": self.running,
                "interval_seconds": self.interval,
                "failure_threshold": self.failure_threshold,
                "success_threshold": self.success_threshold,
                "last_check": self.last_check_timestamp,
                "instances": list(self.check_results.values())
            }
