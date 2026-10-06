"""
Container Manager for Local Container Service Platform
Handles the complete lifecycle of local container instances (process-isolated or Docker).
"""

import os
import sys
import time
import socket
import signal
import subprocess
import threading
import shutil
from datetime import datetime, timezone
from core.storage import Storage

class ContainerInstance:
    def __init__(self, instance_id, port, name="dummy-service", driver="process"):
        self.id = instance_id
        self.port = port
        self.name = name
        self.driver = driver
        self.status = "INITIALIZING"  # INITIALIZING, RUNNING, STOPPED, FAILED
        self.health_status = "UNKNOWN" # HEALTHY, UNHEALTHY, UNKNOWN
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.process = None
        self.pid = None
        self.docker_container_id = None
        self.requests_count = 0
        self.active_connections = 0
        self.last_response_time_ms = 0
        self.consecutive_failures = 0
        self.consecutive_successes = 0

    def to_dict(self):
        return {
            "id": self.id,
            "port": self.port,
            "name": self.name,
            "driver": self.driver,
            "status": self.status,
            "health_status": self.health_status,
            "created_at": self.created_at,
            "pid": self.pid,
            "requests_count": self.requests_count,
            "active_connections": self.active_connections,
            "last_response_time_ms": self.last_response_time_ms,
            "url": f"http://127.0.0.1:{self.port}"
        }


class ContainerManager:
    def __init__(self, storage=None, port_range_start=9001, port_range_end=9099):
        self.storage = storage or Storage()
        self.port_range_start = port_range_start
        self.port_range_end = port_range_end
        self.instances = {}
        self.lock = threading.Lock()
        self.service_script_path = os.path.abspath(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "dummy_service", "service.py")
        )
        self.docker_available = shutil.which("docker") is not None

    def _is_port_in_use(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            return s.connect_ex(('127.0.0.1', port)) == 0

    def _allocate_free_port(self):
        used_ports = {inst.port for inst in self.instances.values()}
        for port in range(self.port_range_start, self.port_range_end + 1):
            if port not in used_ports and not self._is_port_in_use(port):
                return port
        raise RuntimeError("No free ports available in the configured range")

    def create_and_start(self, instance_id=None, port=None, name="dummy-service", driver=None):
        with self.lock:
            if not port:
                port = self._allocate_free_port()
            elif self._is_port_in_use(port):
                raise ValueError(f"Port {port} is already in use")

            if not instance_id:
                instance_id = f"cntr-{port}"

            if instance_id in self.instances:
                raise ValueError(f"Instance ID {instance_id} already exists")

            selected_driver = driver or ("docker" if self.docker_available and driver == "docker" else "process")
            instance = ContainerInstance(instance_id, port, name=name, driver=selected_driver)
            self._start_instance_internal(instance)
            self.instances[instance_id] = instance
            self.storage.save_instance(instance.to_dict())
            self.storage.log_event("CONTAINER_START", f"Container {instance_id} started on port {port}", {"driver": selected_driver})
            return instance

    def _start_instance_internal(self, instance):
        if instance.driver == "docker" and self.docker_available:
            try:
                cmd = [
                    "docker", "run", "-d",
                    "--name", instance.id,
                    "-p", f"{instance.port}:9001",
                    "dummy-service:latest"
                ]
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
                instance.docker_container_id = result.stdout.strip()
                instance.status = "RUNNING"
                instance.health_status = "HEALTHY"
                return
            except Exception as e:
                # Fallback to process driver if Docker fails
                instance.driver = "process"

        # Process-isolated local container execution
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = open(os.path.join(log_dir, f"{instance.id}.log"), "a")

        cmd = [
            sys.executable,
            self.service_script_path,
            "--host", "127.0.0.1",
            "--port", str(instance.port),
            "--id", instance.id,
            "--name", instance.name
        ]
        proc = subprocess.Popen(cmd, stdout=log_file, stderr=log_file, env=os.environ.copy())
        instance.process = proc
        instance.pid = proc.pid
        instance.status = "RUNNING"
        instance.health_status = "HEALTHY"

        # Wait briefly for server socket to bind
        time.sleep(0.3)

    def stop(self, instance_id):
        with self.lock:
            instance = self.instances.get(instance_id)
            if not instance:
                raise KeyError(f"Instance {instance_id} not found")

            if instance.status == "STOPPED":
                return instance

            if instance.driver == "docker" and instance.docker_container_id:
                try:
                    subprocess.run(["docker", "stop", instance.id], check=False)
                except Exception:
                    pass
            elif instance.process:
                try:
                    instance.process.terminate()
                    instance.process.wait(timeout=2.0)
                except Exception:
                    try:
                        instance.process.kill()
                    except Exception:
                        pass
                instance.process = None

            instance.status = "STOPPED"
            instance.health_status = "UNKNOWN"
            self.storage.save_instance(instance.to_dict())
            self.storage.log_event("CONTAINER_STOP", f"Container {instance_id} stopped")
            return instance

    def start(self, instance_id):
        with self.lock:
            instance = self.instances.get(instance_id)
            if not instance:
                raise KeyError(f"Instance {instance_id} not found")

            if instance.status == "RUNNING":
                return instance

            self._start_instance_internal(instance)
            self.storage.save_instance(instance.to_dict())
            self.storage.log_event("CONTAINER_RESUME", f"Container {instance_id} resumed")
            return instance

    def restart(self, instance_id):
        self.stop(instance_id)
        time.sleep(0.5)
        return self.start(instance_id)

    def remove(self, instance_id):
        with self.lock:
            instance = self.instances.get(instance_id)
            if not instance:
                return

            # Ensure stopped
            if instance.status == "RUNNING":
                if instance.driver == "docker" and instance.docker_container_id:
                    try:
                        subprocess.run(["docker", "rm", "-f", instance.id], check=False)
                    except Exception:
                        pass
                elif instance.process:
                    try:
                        instance.process.terminate()
                        instance.process.wait(timeout=1.0)
                    except Exception:
                        instance.process.kill()

            self.instances.pop(instance_id, None)
            self.storage.remove_instance(instance_id)
            self.storage.log_event("CONTAINER_REMOVE", f"Container {instance_id} removed")

    def get_instance(self, instance_id):
        return self.instances.get(instance_id)

    def list_instances(self):
        with self.lock:
            return list(self.instances.values())

    def cleanup_all(self):
        with self.lock:
            for instance_id in list(self.instances.keys()):
                instance = self.instances[instance_id]
                try:
                    if instance.process:
                        instance.process.kill()
                    if instance.driver == "docker" and instance.docker_container_id:
                        subprocess.run(["docker", "rm", "-f", instance.id], check=False)
                except Exception:
                    pass
                instance.status = "STOPPED"
            self.instances.clear()
