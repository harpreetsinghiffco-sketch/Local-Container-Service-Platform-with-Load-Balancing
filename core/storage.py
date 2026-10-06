"""
Persistence Layer for Container Service Platform
Handles SQLite persistence for instances, audit logs, and operational metrics.
"""

import os
import sqlite3
import json
import threading
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "platform.db")

class Storage:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.lock = threading.Lock()
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS instances (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        port INTEGER NOT NULL,
                        driver TEXT NOT NULL,
                        status TEXT NOT NULL,
                        health_status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        requests_count INTEGER DEFAULT 0,
                        meta_json TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        message TEXT NOT NULL,
                        details TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        total_requests INTEGER,
                        active_instances INTEGER,
                        healthy_instances INTEGER,
                        algorithm TEXT
                    )
                """)
                conn.commit()

    def save_instance(self, instance_data):
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO instances (id, name, port, driver, status, health_status, created_at, requests_count, meta_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        status=excluded.status,
                        health_status=excluded.health_status,
                        requests_count=excluded.requests_count,
                        meta_json=excluded.meta_json
                """, (
                    instance_data["id"],
                    instance_data.get("name", "dummy-service"),
                    instance_data["port"],
                    instance_data.get("driver", "process"),
                    instance_data.get("status", "RUNNING"),
                    instance_data.get("health_status", "HEALTHY"),
                    instance_data.get("created_at", datetime.now(timezone.utc).isoformat()),
                    instance_data.get("requests_count", 0),
                    json.dumps(instance_data.get("meta", {}))
                ))
                conn.commit()

    def remove_instance(self, instance_id):
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM instances WHERE id = ?", (instance_id,))
                conn.commit()

    def get_all_instances(self):
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM instances ORDER BY port ASC")
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    item = dict(row)
                    item["meta"] = json.loads(item["meta_json"]) if item.get("meta_json") else {}
                    results.append(item)
                return results

    def log_event(self, event_type, message, details=None):
        ts = datetime.now(timezone.utc).isoformat()
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit_logs (timestamp, event_type, message, details)
                    VALUES (?, ?, ?, ?)
                """, (ts, event_type, message, json.dumps(details) if isinstance(details, (dict, list)) else (details or "")))
                conn.commit()

    def get_audit_logs(self, limit=50):
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
