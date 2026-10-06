"""
Unit tests for Load Balancer scheduling algorithms and failover logic.
"""

import unittest
from core.load_balancer import LoadBalancer
from core.container_manager import ContainerInstance

class MockContainerManager:
    def __init__(self, instances):
        self._instances = instances

    def list_instances(self):
        return self._instances


class TestLoadBalancer(unittest.TestCase):
    def setUp(self):
        self.inst1 = ContainerInstance("cntr-1", 9001)
        self.inst1.status = "RUNNING"
        self.inst1.health_status = "HEALTHY"

        self.inst2 = ContainerInstance("cntr-2", 9002)
        self.inst2.status = "RUNNING"
        self.inst2.health_status = "HEALTHY"

        self.inst3 = ContainerInstance("cntr-3", 9003)
        self.inst3.status = "RUNNING"
        self.inst3.health_status = "HEALTHY"

        self.instances = [self.inst1, self.inst2, self.inst3]
        self.mgr = MockContainerManager(self.instances)
        self.lb = LoadBalancer(self.mgr, algorithm="round_robin")

    def test_round_robin_selection(self):
        selected = [self.lb.select_instance().id for _ in range(6)]
        expected = ["cntr-1", "cntr-2", "cntr-3", "cntr-1", "cntr-2", "cntr-3"]
        self.assertEqual(selected, expected)

    def test_least_connections_selection(self):
        self.lb.set_algorithm("least_connections")
        self.inst1.active_connections = 5
        self.inst2.active_connections = 1
        self.inst3.active_connections = 3

        selected = self.lb.select_instance()
        self.assertEqual(selected.id, "cntr-2")

    def test_ip_hash_consistency(self):
        self.lb.set_algorithm("ip_hash")
        ip = "192.168.1.50"
        first = self.lb.select_instance(client_ip=ip).id
        second = self.lb.select_instance(client_ip=ip).id
        third = self.lb.select_instance(client_ip=ip).id
        self.assertEqual(first, second)
        self.assertEqual(second, third)

    def test_unhealthy_instances_excluded_from_pool(self):
        self.inst2.health_status = "UNHEALTHY"
        healthy_pool = [i.id for i in self.lb.get_healthy_instances()]
        self.assertNotIn("cntr-2", healthy_pool)
        self.assertEqual(len(healthy_pool), 2)

        # Round robin should only cycle between cntr-1 and cntr-3
        selected = [self.lb.select_instance().id for _ in range(4)]
        self.assertNotIn("cntr-2", selected)

    def test_empty_pool_handling(self):
        for inst in self.instances:
            inst.status = "STOPPED"
        self.assertIsNone(self.lb.select_instance())


if __name__ == "__main__":
    unittest.main()
