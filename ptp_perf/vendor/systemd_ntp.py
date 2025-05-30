import asyncio
import logging
import subprocess
import typing
from dataclasses import dataclass

from ptp_perf.invoke.invocation import Invocation
from ptp_perf.vendor.vendor import Vendor

if typing.TYPE_CHECKING:
    from ptp_perf.models import PTPEndpoint

@dataclass
class SystemDNTPVendor(Vendor):
    id: str = "systemd-ntp"
    name: str = "SystemD-NTP"

    @property
    def running(self):
        return 'NTP service: active' in subprocess.check_output("timedatectl").decode()

    async def run(self, endpoint: "PTPEndpoint"):
        await self.toggle_ntp_service(active=True)
        try:
            while True:
                await asyncio.sleep(1)
        finally:
            await self.toggle_ntp_service(active=False)

    async def toggle_ntp_service(self, active: bool):
        logging.debug(("Activating" if active else "Deactivating") + " SystemD NTP service...")
        await Invocation.of_command("timedatectl", "set-ntp", "true" if active else "false").as_privileged().hide_unless_failure().run()

    async def check_clock_synchronized(self):
        """Check whether the clock is currently synchronized via NTP"""
        timedatectl = await Invocation.of_command("timedatectl").hide_unless_failure().hide_unless_failure().run()
        return "System clock synchronized: yes" in timedatectl.output
