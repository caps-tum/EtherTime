import unittest

from ptp_perf.models.data_container import DataContainer


class TestDataContainer(unittest.TestCase):

    def test_load(self):
        data_container = DataContainer()
        data_container.run()
        print(data_container.data)
        self.assertGreater(len(data_container.data), 0)
