import asyncio
from unittest import TestCase

import config
from config import current_configuration
from machine import Machine
from util import setup_logging
from vendor.linuxptp import LinuxPTPVendor
from vendor.vendor import Vendor


class TestLinuxPTPRest(TestCase):



    @classmethod
    def setUpClass(cls):
        setup_logging()

    async def restart_vendor(self, vendor: Vendor):
        await vendor.start()
        await asyncio.sleep(10)
        await vendor.restart(kill=True)
        await asyncio.sleep(10)
        await vendor.stop()

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
