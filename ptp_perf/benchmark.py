import logging
from datetime import datetime, timedelta

import util
from adapters.fault_generators import SoftwareFaultGenerator
from adapters.performance_degraders import NetworkPerformanceDegrader, CPUPerformanceDegrader
from constants import PTPPERF_REPOSITORY_ROOT
from ptp_perf.invoke.invocation import Invocation
from ptp_perf.machine import Machine
from ptp_perf.models import PTPProfile, PTPEndpoint
from util import async_wait_for_condition, setup_logging
from utilities.multi_task_controller import MultiTaskController
from vendor.registry import VendorDB


async def benchmark(profile_id: int, machine_id: str):
    profile: PTPProfile = PTPProfile.objects.get(id=profile_id)

    try:
        endpoint: PTPEndpoint = PTPEndpoint.objects.filter(profile=profile, machine_id=machine_id).get()
    except PTPEndpoint.DoesNotExist:
        endpoint = PTPEndpoint(profile=profile, machine_id=machine_id)
        endpoint.save()

    configuration = profile.configuration
    background_tasks = MultiTaskController()

    # TODO: Capture log to database
    profile_log = PTPPERF_REPOSITORY_ROOT.joinpath("data").joinpath("logs").joinpath(f"profile_{profile.id}.log")
    profile_log.parent.mkdir(exist_ok=True)

    setup_logging(log_file=str(profile_log))

    try:
        profile.vendor.create_configuration_file(endpoint)

        await synchronize_time_ntp(configuration.machine)

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
        if profile.benchmark.fault_tolerance_software_fault_interval is not None and profile.benchmark.fault_tolerance_software_fault_machine == profile.configuration.machine.id:
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
        profile.log = profile_log.read_text()

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
