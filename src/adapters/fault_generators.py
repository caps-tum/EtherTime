import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from profiles.base_profile import BaseProfile
from vendor.vendor import Vendor


@dataclass
class SoftwareFaultGenerator:
    profile: BaseProfile
    log_history: str = ""

    def log(self, message: str):
        output = f"{datetime.now()}: {message}"
        self.log_history += output + "\n"
        logging.info(output)

    async def run(self, vendor: Vendor, interval: timedelta):
        # We do this until we are cancelled
        self.log(f"Scheduling software faults every {self.profile.benchmark.fault_tolerance_software_fault_interval} on {self.profile.configuration.machine.id}")
        try:
            while True:
                await asyncio.sleep(interval.total_seconds())
                self.log(f"Scheduled software fault imminent on {self.profile.configuration.machine}.")
                await vendor.restart(kill=True)
        finally:
            if self.log_history is not None:
                self.profile.raw_data.update(software_fault_log=self.log_history)
