import asyncio
import logging
from asyncio import CancelledError
from contextlib import AsyncExitStack
from datetime import datetime, timedelta

import util
from adapters.performance_degraders import NetworkPerformanceDegrader, CPUPerformanceDegrader
from config import current_configuration
from constants import PTPPERF_REPOSITORY_ROOT, CONFIG_DIR, LOCAL_DIR
from invoke.invocation import Invocation
from profiles.base_profile import BaseProfile
from util import async_wait_for_condition, setup_logging
from vendor.registry import VendorDB
from vendor.vendor import Vendor


async def prepare():
    """Ensures all vendors are stopped, synchronizes the time over NTP and then steps the clock to get reproducible starting conditions."""
    pass

async def restart_vendor_repeatedly(vendor: Vendor, interval: timedelta):
    # We do this until we are cancelled
    try:
        while True:
            await asyncio.sleep(interval.total_seconds())
            logging.info(f"Scheduled software fault imminent on {current_configuration.machine}.")
            await vendor.restart(kill=True)
    except CancelledError:
        pass

async def prompt_repeatedly(fault_tolerance_prompt_interval: timedelta, fault_tolerance_prompt_downtime: timedelta):
    # We do this until we are cancelled
    # Do some math so that we actually trigger at each interval
    actual_interval = fault_tolerance_prompt_interval - fault_tolerance_prompt_downtime
    try:
        await asyncio.sleep(fault_tolerance_prompt_downtime.total_seconds())
        while True:
            await asyncio.sleep(actual_interval.total_seconds())
            logging.warning(f"======= Unplug the hardware NOW! ========")
            await asyncio.sleep(fault_tolerance_prompt_downtime.total_seconds())
            logging.warning(f"======= Replug the hardware NOW! ========")
    except CancelledError:
        pass


async def benchmark(profile: BaseProfile):

    profile.machine_id = current_configuration.machine.id
    background_tasks = AsyncExitStack()

    profile_log = CONFIG_DIR.joinpath(f"profile_{profile.id}.log")

    setup_logging(log_file=str(profile_log))

    try:
        profile.vendor.create_configuration_file(profile)

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

        # Actually start the benchmark

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

        # Launch background hardware prompts if necessary. We only do this on the ptp_master
        if profile.benchmark.fault_tolerance_prompt_interval is not None and current_configuration.machine.ptp_master:
            logging.warning(f"Will prompt repeatedly every {profile.benchmark.fault_tolerance_prompt_interval} so that you can manually power cycle the hardware.")
            prompt_task = asyncio.create_task(prompt_repeatedly(profile.benchmark.fault_tolerance_prompt_interval, profile.benchmark.fault_tolerance_prompt_downtime))
            background_tasks.callback(lambda: prompt_task.cancel())

        # Launch background "crashes" of vendor if necessary
        if profile.benchmark.fault_tolerance_software_fault_interval is not None and profile.benchmark.fault_tolerance_software_fault_machine == current_configuration.machine.id:
            logging.info(f"Scheduling software faults every {profile.benchmark.fault_tolerance_software_fault_interval} on {current_configuration.machine.id}")
            restart_task = asyncio.create_task(restart_vendor_repeatedly(profile.vendor, profile.benchmark.fault_tolerance_software_fault_interval))
            background_tasks.callback(lambda: restart_task.cancel())

        logging.info(f"Starting {profile.vendor}...")
        await profile.vendor.start()
        logging.info(f"Benchmarking for {profile.benchmark.duration}...")
        await asyncio.sleep(profile.benchmark.duration.total_seconds())
    except Exception as e:
        # On error, note down that the benchmark failed, but still save it.
        profile.success = False
        logging.error(f"Benchmark {profile} failed: {e}")
        util.log_exception(e)

    await profile.vendor.stop()
    logging.info(f"Stopped {profile.vendor}...")

    await background_tasks.aclose()

    profile.vendor.collect_data(profile)

    profile.log = profile_log.read_text()

    return profile
