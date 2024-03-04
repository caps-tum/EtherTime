import logging
from datetime import datetime, timedelta

from ptp_perf import util
from ptp_perf.adapters.fault_generators import SoftwareFaultGenerator
from ptp_perf.adapters.performance_degraders import NetworkPerformanceDegrader, CPUPerformanceDegrader
from ptp_perf.constants import PTPPERF_REPOSITORY_ROOT
from ptp_perf.invoke.invocation import Invocation
from ptp_perf.machine import Machine
from ptp_perf.models import PTPProfile, PTPEndpoint
from ptp_perf.util import async_wait_for_condition
from ptp_perf.utilities.logging import LogToDBLogRecordHandler
from ptp_perf.utilities.multi_task_controller import MultiTaskController
from ptp_perf.vendor.registry import VendorDB


async def benchmark(endpoint_id: str):
    endpoint: PTPEndpoint = await PTPEndpoint.objects.aget(id=endpoint_id)
    profile: PTPProfile = endpoint.profile

    handler = LogToDBLogRecordHandler(endpoint)
    handler.install()

    background_tasks = MultiTaskController()

    try:
        profile.vendor.create_configuration_file(endpoint)

        await synchronize_time_ntp(endpoint.machine)

        # Actually start the benchmark

        if profile.benchmark.artificial_load_network > 0:
            # Start iPerf
            artificial_network_load = NetworkPerformanceDegrader(profile)
            background_tasks.add_coroutine(artificial_network_load.run(), label="iPerf")
        if profile.benchmark.artificial_load_cpu > 0:
            # Start Stress_ng
            artificial_cpu_load = CPUPerformanceDegrader(profile)
            background_tasks.add_coroutine(artificial_cpu_load.run(), label="Stress-NG")

        # Launch background "crashes" of vendor if necessary
        if profile.benchmark.fault_tolerance_software_fault_interval is not None and profile.benchmark.fault_tolerance_software_fault_machine == endpoint.machine_id:
            fault_generator = SoftwareFaultGenerator(profile)
            background_tasks.add_coroutine(fault_generator.run())

        logging.info(f"Starting {profile.vendor}...")
        background_tasks.add_coroutine(
            profile.vendor.run(profile), label=f"{profile.vendor.name}"
        )
        logging.info(f"Benchmarking for {profile.benchmark.duration}...")
        await background_tasks.run_for(profile.benchmark.duration)

        profile.success = True
    except Exception as e:
        # On error, note down that the benchmark failed, but still save it.
        profile.success = False
        logging.error(f"Benchmark {profile.id} failed: {e}")
        util.log_exception(e, force_traceback=True)

    try:
        logging.info(f"Stopping background tasks...")
        await background_tasks.cancel_pending_tasks()
    except Exception as e:
        # On error, note down that the benchmark failed, but still save it.
        profile.success = False
        logging.error(f"Benchmark {profile} failed: {e}")
        util.log_exception(e, force_traceback=True)
    finally:
        profile.vendor.collect_data(profile)

    handler.uninstall()

    return profile


async def synchronize_time_ntp(local_machine: Machine, use_initial_clock_offset: bool = True):
    # Synchronize the time to NTP
    logging.info(f"Starting initial time synchronization via SystemD-NTP.")
    systemd_ntp_vendor = VendorDB.SYSTEMD_NTP
    await systemd_ntp_vendor.toggle_ntp_service(active=True)
    await async_wait_for_condition(
        systemd_ntp_vendor.check_clock_synchronized, target=True, timeout=timedelta(seconds=10), quiet=True
    )
    await systemd_ntp_vendor.toggle_ntp_service(active=False)

    # Step the clock using PPSi tool
    target_clock_offset = local_machine.initial_clock_offset if use_initial_clock_offset else None
    if target_clock_offset is not None:
        logging.info(f"Adjusting node {local_machine} time by {target_clock_offset}.")
        await Invocation.of_command(
            "lib/ppsi/tools/jmptime", str(target_clock_offset.total_seconds())
        ).as_privileged().set_working_directory(PTPPERF_REPOSITORY_ROOT).run()
    logging.info(f"{local_machine} time is now {datetime.now()}")
