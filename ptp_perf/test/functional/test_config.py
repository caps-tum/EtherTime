import unittest

import ptp_perf.config


class TestConfig(unittest.TestCase):

    def test_effective_force_slave(self):
        cluster = ptp_perf.config.CLUSTER_PI

        # Both slaves when failover not active
        self.assertEqual(True, cluster.machine_by_id("rpi07").ptp_force_slave_effective(failover_active=False))
        self.assertEqual(True, cluster.machine_by_id("rpi08").ptp_force_slave_effective(failover_active=False))
        self.assertEqual(False, cluster.machine_by_id("rpi06").ptp_force_slave_effective(failover_active=False))

        # One master when failover active
        self.assertEqual(False, cluster.machine_by_id("rpi07").ptp_force_slave_effective(failover_active=True))
        self.assertEqual(True, cluster.machine_by_id("rpi08").ptp_force_slave_effective(failover_active=True))
        self.assertEqual(False, cluster.machine_by_id("rpi06").ptp_force_slave_effective(failover_active=True))

