"""
Unit tests for Container Manager port allocation, lifecycle, and storage interaction.
"""

import unittest
from unittest.mock import MagicMock
from core.container_manager import ContainerManager, ContainerInstance

class TestContainerManager(unittest.TestCase):
    def setUp(self):
        self.mock_storage = MagicMock()
        self.mgr = ContainerManager(storage=self.mock_storage, port_range_start=9100, port_range_end=9110)

    def test_port_allocation(self):
        port1 = self.mgr._allocate_free_port()
        self.assertEqual(port1, 9100)
        
        # Simulate instance using port 9100
        inst = ContainerInstance("cntr-test", 9100)
        self.mgr.instances["cntr-test"] = inst

        port2 = self.mgr._allocate_free_port()
        self.assertEqual(port2, 9101)

    def test_instance_dict_serialization(self):
        inst = ContainerInstance("test-inst", 9005, name="api-v1")
        inst.status = "RUNNING"
        inst.health_status = "HEALTHY"
        d = inst.to_dict()
        self.assertEqual(d["id"], "test-inst")
        self.assertEqual(d["port"], 9005)
        self.assertEqual(d["status"], "RUNNING")
        self.assertEqual(d["health_status"], "HEALTHY")
        self.assertEqual(d["url"], "http://127.0.0.1:9005")

    def test_remove_instance(self):
        inst = ContainerInstance("to-remove", 9105)
        self.mgr.instances["to-remove"] = inst
        self.mgr.remove("to-remove")
        self.assertNotIn("to-remove", self.mgr.instances)
        self.mock_storage.remove_instance.assert_called_with("to-remove")


if __name__ == "__main__":
    unittest.main()
