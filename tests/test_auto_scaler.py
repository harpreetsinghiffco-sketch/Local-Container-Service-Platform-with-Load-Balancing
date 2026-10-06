"""
Unit tests for Auto Scaler capacity calculation and thresholds.
"""

import unittest
from unittest.mock import MagicMock
from core.auto_scaler import AutoScaler
from core.container_manager import ContainerInstance

class TestAutoScaler(unittest.TestCase):
    def setUp(self):
        self.mock_cm = MagicMock()
        self.mock_lb = MagicMock()
        self.mock_storage = MagicMock()

        self.as_engine = AutoScaler(
            container_manager=self.mock_cm,
            load_balancer=self.mock_lb,
            storage=self.mock_storage,
            min_instances=2,
            max_instances=5,
            target_rps_per_instance=5.0,
            cooldown_seconds=0 # instant for tests
        )

    def test_minimum_instance_enforcement(self):
        self.as_engine.enabled = True
        self.mock_lb.get_healthy_instances.return_value = [ContainerInstance("c1", 9001)]
        self.as_engine.last_requests_sample = 0
        self.mock_lb.total_requests = 0

        self.as_engine._evaluate_scale()
        # Should call create_and_start once to reach min_instances=2
        self.mock_cm.create_and_start.assert_called_once()

    def test_scale_up_trigger_on_high_load(self):
        self.as_engine.enabled = True
        inst1 = ContainerInstance("c1", 9001)
        inst2 = ContainerInstance("c2", 9002)
        self.mock_lb.get_healthy_instances.return_value = [inst1, inst2]
        
        # Simulate high RPS: 20 req/s with 2 instances (target is 5 rps/instance, capacity is 10)
        self.as_engine.current_rps = 20.0
        self.as_engine.last_sample_time = 0 # force time delta
        self.as_engine.last_requests_sample = 0
        self.mock_lb.total_requests = 100

        self.as_engine._evaluate_scale()
        self.mock_cm.create_and_start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
