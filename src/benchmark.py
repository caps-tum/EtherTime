import asyncio
import logging
import time
from datetime import timedelta, datetime

from config import current_configuration
from constants import PTPPERF_REPOSITORY_ROOT
from invoke.invocation import Invocation
from profiles.base_profile import BaseProfile
from util import async_wait_for_condition
from vendor.registry import VendorDB


async def prepare():
    """Ensures all vendors are stopped, synchronizes the time over NTP and then steps the clock to get reproducible starting conditions."""
    # Stop everything
    for vendor in VendorDB.all():
        await vendor.stop()

    # Synchronize the time to NTP
    logging.info(f"Starting initial time synchronization via SystemD-NTP.")
    systemd_ntp_vendor = VendorDB.SYSTEMD_NTP
    await systemd_ntp_vendor.start()
    await async_wait_for_condition(systemd_ntp_vendor.check_clock_synchronized, target=True)
    await systemd_ntp_vendor.stop()

    # Step the clock using PPSi tool
    target_clock_offset = current_configuration.machine.initial_clock_offset
    if target_clock_offset is not None:
        logging.info(f"Adjusting node {current_configuration.machine} time by {target_clock_offset}.")
        await Invocation.of_command(
            "lib/ppsi/tools/jmptime", str(target_clock_offset.total_seconds())
        ).as_privileged().set_working_directory(PTPPERF_REPOSITORY_ROOT).run()

    logging.info(f"{current_configuration.machine} time is now {datetime.now()}")


async def benchmark(profile: BaseProfile):

    profile.machine_id = current_configuration.machine.id

    try:
        logging.info(f"Starting {profile.vendor}...")
        await profile.vendor.start()
        logging.info(f"Benchmarking for {profile.benchmark.duration}...")
        await asyncio.sleep(profile.benchmark.duration.total_seconds())
    finally:
        await profile.vendor.stop()
        logging.info(f"Stopped {profile.vendor}...")

    profile.vendor.collect_data(profile)
    return profile
