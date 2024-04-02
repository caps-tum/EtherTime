import asyncio
from unittest import TestCase

from ptp_perf import config
from ptp_perf.machine import Machine
from ptp_perf.util import setup_logging
from ptp_perf.utilities.multi_task_controller import MultiTaskController
from ptp_perf.vendor.linuxptp import LinuxPTPVendor
from ptp_perf.vendor.vendor import Vendor


class TestLinuxPTPRest(TestCase):



    @classmethod
    def setUpClass(cls):
        setup_logging()

    async def restart_vendor(self, vendor: Vendor):
        tasks = MultiTaskController()
        tasks.add_coroutine(vendor.run())
        await asyncio.sleep(10)
        await vendor.restart(kill=True)
        await asyncio.sleep(10)
        await tasks.cancel_pending_tasks()

    def test_create(self):
        local_machine = Machine(
            id="local", address="127.0.0.1",
            ptp_interface="eth0", ptp_use_phc2sys=False, ptp_software_timestamping=True,
        )
        config.set_machine_direct(local_machine)

        vendor = LinuxPTPVendor()

        if not vendor.installed:
            self.skipTest(f"Vendor {vendor} not installed.")

        asyncio.run(self.restart_vendor(vendor))
