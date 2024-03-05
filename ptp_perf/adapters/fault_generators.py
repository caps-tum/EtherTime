import asyncio
from datetime import timedelta, datetime

from ptp_perf.adapters.adapter import Adapter


class SoftwareFaultGenerator(Adapter):
    log_source = "fault-generator"

    async def run(self):
        vendor = self.endpoint.profile.vendor
        interval = self.endpoint.benchmark.fault_tolerance_software_fault_interval

        # We do this until we are cancelled
        self.log(f"Scheduling software faults every {interval} on {self.endpoint.machine}")
        # Don't drift
        next_wakeup = datetime.now() + interval
        while True:
            await asyncio.sleep((next_wakeup - datetime.now()).total_seconds())
            if vendor.running:
                self.log(f"Scheduled software fault imminent on {self.endpoint.machine}.")
                await vendor.restart(kill=True)
                self.log(f"Scheduled software fault resolved on {self.endpoint.machine}.")
            next_wakeup += interval
