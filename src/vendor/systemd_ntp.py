import logging
import subprocess
from dataclasses import dataclass

from invoke.invocation import Invocation
from vendor.vendor import Vendor


@dataclass
class SystemDNTPVendor(Vendor):
    id: str = "systemd-ntp"
    name: str = "SystemD-NTP"

    @property
    def running(self):
        return 'NTP service: active' in subprocess.check_output("timedatectl").decode()

    async def start(self):
        await self.toggle_ntp_service(active=True)

    async def stop(self):
        await self.toggle_ntp_service(active=False)

    async def toggle_ntp_service(self, active: bool):
        logging.info(("Activating" if active else "Deactivating") + " SystemD NTP service...")
        await Invocation.of_command("timedatectl", "set-ntp", "true" if active else "false").as_privileged().hide_unless_failure().run()

    async def check_clock_synchronized(self):
        """Check whether the clock is currently synchronized via NTP"""
        timedatectl = await Invocation.of_command("timedatectl").hide_unless_failure().hide_unless_failure().run()
        return "System clock synchronized: yes" in timedatectl.output
