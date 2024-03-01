import asyncio
from datetime import timedelta, datetime

from ptp_perf.adapters.adapter import Adapter


class SoftwareFaultGenerator(Adapter):
    raw_data_log_key: str = "software_fault_log"

    async def run(self):
        vendor = self.profile.vendor
        interval = self.profile.benchmark.fault_tolerance_software_fault_interval

        # We do this until we are cancelled
        self.log(f"Scheduling software faults every {interval} on {self.profile.configuration.machine.id}")
        # Don't drift
        next_wakeup = datetime.now() + interval
        while True:
            await asyncio.sleep((next_wakeup - datetime.now()).total_seconds())
            if vendor.running:
                self.log(f"Scheduled software fault imminent on {self.profile.configuration.machine}.")
                await vendor.restart(kill=True)
            next_wakeup += interval
