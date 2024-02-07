import asyncio
import logging
from contextlib import AsyncExitStack
from datetime import datetime

from adapters.performance_degraders import NetworkPerformanceDegrader, CPUPerformanceDegrader
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

    background_tasks = AsyncExitStack()

    try:
        if profile.benchmark.artificial_load_network > 0:
            # Start iPerf
            artificial_network_load = NetworkPerformanceDegrader()
            await artificial_network_load.start(profile.benchmark.artificial_load_network, profile.benchmark.artificial_load_network_dscp_priority)
            background_tasks.push_async_callback(artificial_network_load.stop)
        if profile.benchmark.artificial_load_cpu > 0:
            # Start Stress_ng
            artificial_cpu_load = CPUPerformanceDegrader()
            await artificial_cpu_load.start(profile.benchmark.artificial_load_cpu)
            background_tasks.push_async_callback(artificial_cpu_load.stop)

        logging.info(f"Starting {profile.vendor}...")
        await profile.vendor.start()
        logging.info(f"Benchmarking for {profile.benchmark.duration}...")
        await asyncio.sleep(profile.benchmark.duration.total_seconds())
    finally:
        await profile.vendor.stop()
        logging.info(f"Stopped {profile.vendor}...")

        await background_tasks.aclose()

    profile.vendor.collect_data(profile)
    return profile
