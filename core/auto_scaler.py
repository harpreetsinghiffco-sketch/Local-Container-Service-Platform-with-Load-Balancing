"""
Auto-Scaler for Local Container Service Platform
Monitors traffic load and dynamically scales container instances up or down based on policies.
"""

import time
import threading
from datetime import datetime, timezone

class AutoScaler:
    def __init__(self, container_manager, load_balancer, storage=None,
                 min_instances=2, max_instances=6, target_rps_per_instance=5.0, cooldown_seconds=8):
        self.container_manager = container_manager
        self.load_balancer = load_balancer
        self.storage = storage
        self.min_instances = min_instances
        self.max_instances = max_instances
        self.target_rps = target_rps_per_instance
        self.cooldown_seconds = cooldown_seconds
        
        self.enabled = False
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        
        self.last_scale_time = 0
        self.last_requests_sample = 0
        self.last_sample_time = time.time()
        self.current_rps = 0.0
        self.scale_events = []

    def set_config(self, enabled=None, min_inst=None, max_inst=None, target_rps=None):
        with self.lock:
            if enabled is not None:
                self.enabled = bool(enabled)
            if min_inst is not None:
                self.min_instances = max(1, int(min_inst))
            if max_inst is not None:
                self.max_instances = max(self.min_instances, int(max_inst))
            if target_rps is not None:
                self.target_rps = max(1.0, float(target_rps))
        if self.storage:
            self.storage.log_event("AUTOSCALER_CONFIG", "AutoScaler settings updated", {
                "enabled": self.enabled,
                "min": self.min_instances,
                "max": self.max_instances,
                "target_rps": self.target_rps
            })

    def start(self):
        with self.lock:
            if self.running:
                return
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True, name="AutoScalerThread")
            self.thread.start()

    def stop(self):
        with self.lock:
            self.running = False

    def _monitor_loop(self):
        while self.running:
            self._evaluate_scale()
            time.sleep(2.0)

    def _evaluate_scale(self):
        now = time.time()
        time_delta = now - self.last_sample_time
        if time_delta < 1.0:
            return

        with self.load_balancer.lock:
            req_delta = self.load_balancer.total_requests - self.last_requests_sample
            self.last_requests_sample = self.load_balancer.total_requests
            self.last_sample_time = now

        self.current_rps = round(req_delta / time_delta, 2)
        
        if not self.enabled:
            return

        healthy_instances = self.load_balancer.get_healthy_instances()
        current_count = len(healthy_instances)
        now_ts = time.time()

        # Enforce minimum count
        if current_count < self.min_instances:
            to_add = self.min_instances - current_count
            for _ in range(to_add):
                try:
                    new_inst = self.container_manager.create_and_start()
                    self._record_scale_event("SCALE_UP", f"Enforced min instances ({self.min_instances})", new_inst.id)
                except Exception as e:
                    break
            return

        # Check cooldown
        if (now_ts - self.last_scale_time) < self.cooldown_seconds:
            return

        # Check Scale-Up condition: Load exceeds target capacity
        capacity = current_count * self.target_rps
        if self.current_rps > capacity and current_count < self.max_instances:
            try:
                new_inst = self.container_manager.create_and_start()
                self.last_scale_time = now_ts
                self._record_scale_event(
                    "SCALE_UP",
                    f"RPS ({self.current_rps}) exceeded capacity ({capacity:.1f}). Adding instance.",
                    new_inst.id
                )
            except Exception as e:
                pass

        # Check Scale-Down condition: Load is low and we have more than min instances
        elif self.current_rps < ((current_count - 1) * self.target_rps * 0.5) and current_count > self.min_instances:
            # Pick the instance with least active requests
            candidates = sorted(healthy_instances, key=lambda inst: inst.requests_count)
            if candidates:
                to_remove = candidates[0]
                try:
                    self.container_manager.remove(to_remove.id)
                    self.last_scale_time = now_ts
                    self._record_scale_event(
                        "SCALE_DOWN",
                        f"RPS ({self.current_rps}) cooled down. Gracefully removed instance {to_remove.id}.",
                        to_remove.id
                    )
                except Exception:
                    pass

    def _record_scale_event(self, action, reason, instance_id):
        event = {
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "action": action,
            "reason": reason,
            "instance_id": instance_id,
            "current_rps": self.current_rps
        }
        self.scale_events.insert(0, event)
        if len(self.scale_events) > 20:
            self.scale_events.pop()
        if self.storage:
            self.storage.log_event(action, reason, {"instance_id": instance_id, "rps": self.current_rps})

    def get_status(self):
        with self.lock:
            return {
                "enabled": self.enabled,
                "current_rps": self.current_rps,
                "min_instances": self.min_instances,
                "max_instances": self.max_instances,
                "target_rps_per_instance": self.target_rps,
                "cooldown_seconds": self.cooldown_seconds,
                "last_scale_time": self.last_scale_time,
                "recent_events": list(self.scale_events[:10])
            }
