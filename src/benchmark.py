import asyncio
import logging
from asyncio import CancelledError, Task
from contextlib import AsyncExitStack
from datetime import datetime, timedelta
from typing import List, Coroutine

import util
from adapters.performance_degraders import NetworkPerformanceDegrader, CPUPerformanceDegrader
from config import current_configuration
from constants import PTPPERF_REPOSITORY_ROOT
from invoke.invocation import Invocation
from profiles.base_profile import BaseProfile
from util import async_wait_for_condition, setup_logging
from vendor.registry import VendorDB
from vendor.vendor import Vendor


class BenchmarkTaskController:
    background_tasks: List[Task]
    exit_stack: AsyncExitStack

    async def run_for(self, duration: timedelta = None):
        if duration is not None:
            timeout = duration.total_seconds()
        else:
            timeout = None

        try:
            await asyncio.wait(
                *self.background_tasks, timeout=timeout, return_when=asyncio.FIRST_COMPLETED,
            )
        except TimeoutError:
            pass

    async def cancel_pending_tasks(self):
        await self.exit_stack.aclose()
        self.background_tasks.clear()


    @staticmethod
    async def _stop_task(task: Task):
        try:
            if not task.done():
                task.cancel()
                await task
        finally:
            task.result()

    def add_coroutine(self, coroutine: Coroutine, label: str = None):
        task = asyncio.create_task(coroutine, name=label)
        self.add_task(task)

    def add_task(self, task: Task):
        self.background_tasks.append(task)
        self.exit_stack.push_async_callback(self._stop_task, task)


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
    background_tasks = BenchmarkTaskController()

    profile_log = PTPPERF_REPOSITORY_ROOT.joinpath("data").joinpath("logs").joinpath(f"profile_{profile.id}.log")
    profile_log.parent.mkdir(exist_ok=True)

    setup_logging(log_file=str(profile_log))

    try:
        profile.vendor.create_configuration_file(profile)

        # Stop everything
        for vendor in VendorDB.all():
            await vendor.stop()

        # Synchronize the time to NTP
        logging.info(f"Starting initial time synchronization via SystemD-NTP.")
        systemd_ntp_vendor = VendorDB.SYSTEMD_NTP
        background_tasks.add_coroutine(systemd_ntp_vendor.run())
        await async_wait_for_condition(systemd_ntp_vendor.check_clock_synchronized, target=True)
        await background_tasks.cancel_pending_tasks()

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
            background_tasks.add_coroutine(
                artificial_network_load.run(
                    profile.benchmark.artificial_load_network, profile.benchmark.artificial_load_network_dscp_priority
                )
            )
        if profile.benchmark.artificial_load_cpu > 0:
            # Start Stress_ng
            artificial_cpu_load = CPUPerformanceDegrader()
            background_tasks.add_coroutine(
                artificial_cpu_load.run(profile.benchmark.artificial_load_cpu)
            )


        # Launch background hardware prompts if necessary. We only do this on the ptp_master
        if profile.benchmark.fault_tolerance_prompt_interval is not None and current_configuration.machine.ptp_master:
            logging.warning(f"Will prompt repeatedly every {profile.benchmark.fault_tolerance_prompt_interval} so that you can manually power cycle the hardware.")
            background_tasks.add_coroutine(
                prompt_repeatedly(profile.benchmark.fault_tolerance_prompt_interval, profile.benchmark.fault_tolerance_prompt_downtime)
            )

        # Launch background "crashes" of vendor if necessary
        if profile.benchmark.fault_tolerance_software_fault_interval is not None and profile.benchmark.fault_tolerance_software_fault_machine == current_configuration.machine.id:
            logging.info(f"Scheduling software faults every {profile.benchmark.fault_tolerance_software_fault_interval} on {current_configuration.machine.id}")
            background_tasks.add_coroutine(
                restart_vendor_repeatedly(profile.vendor, profile.benchmark.fault_tolerance_software_fault_interval)
            )

        logging.info(f"Starting {profile.vendor}...")
        background_tasks.add_coroutine(
            profile.vendor.run(), label=f"{profile.vendor.name}"
        )
        logging.info(f"Benchmarking for {profile.benchmark.duration}...")
        await background_tasks.run_for(profile.benchmark.duration)
    except Exception as e:
        # On error, note down that the benchmark failed, but still save it.
        profile.success = False
        logging.error(f"Benchmark {profile} failed: {e}")
        util.log_exception(e, force_traceback=True)

    try:
        logging.info(f"Stopping background tasks {profile.vendor}...")
        await background_tasks.cancel_pending_tasks()
    except Exception as e:
        # On error, note down that the benchmark failed, but still save it.
        profile.success = False
        logging.error(f"Benchmark {profile} failed: {e}")
        util.log_exception(e, force_traceback=True)
    finally:
        profile.vendor.collect_data(profile)
        profile.log = profile_log.read_text()

    return profile
