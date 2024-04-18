import logging
from datetime import datetime, timedelta

from ptp_perf import util
from ptp_perf.adapters.fault_generators import SoftwareFaultGenerator
from ptp_perf.adapters.performance_degraders import NetworkPerformanceDegrader, StressNGPerformanceDegrader
from ptp_perf.constants import PTPPERF_REPOSITORY_ROOT
from ptp_perf.invoke.invocation import Invocation
from ptp_perf.machine import Machine
from ptp_perf.models import PTPProfile, PTPEndpoint
from ptp_perf.util import async_wait_for_condition
from ptp_perf.utilities.django_utilities import get_server_datetime
from ptp_perf.utilities.logging import LogToDBLogRecordHandler
from ptp_perf.utilities.multi_task_controller import MultiTaskController
from ptp_perf.vendor.registry import VendorDB


async def benchmark(endpoint_id: str):
    endpoint: PTPEndpoint = await PTPEndpoint.objects.select_related('profile').aget(id=endpoint_id)
    profile: PTPProfile = endpoint.profile

    is_first_startup = endpoint.restart_count == 0
    endpoint.restart_count += 1
    await endpoint.asave()


    handler = LogToDBLogRecordHandler(endpoint)
    handler.install()

    background_tasks = MultiTaskController()

    try:
        profile.vendor.create_configuration_file(endpoint)

        if is_first_startup:
            # First time we set a predictable clock offset at the beginning of the benchmark
            # When restarting (due to e.g. hardware fault), we leave the clock at its default
            await synchronize_time_ntp(endpoint.machine)
            await clock_jump(endpoint.machine, endpoint.benchmark.setup_use_initial_clock_offset)

        # Actually start the benchmark

        if profile.benchmark.artificial_load_network > 0:
            # Start iPerf
            artificial_network_load = NetworkPerformanceDegrader(endpoint)
            background_tasks.add_coroutine(artificial_network_load.run(), label="iPerf")
        if profile.benchmark.artificial_load_cpu > 0 or profile.benchmark.artificial_load_aux:
            # Start Stress_ng
            artificial_load = StressNGPerformanceDegrader(endpoint)
            background_tasks.add_coroutine(artificial_load.run(), label="Stress-NG")

        # Launch background "crashes" of vendor if necessary
        fault_machine = profile.cluster.machine_by_type(profile.benchmark.fault_location)
        if profile.benchmark.fault_software and fault_machine.id == endpoint.machine_id:
            fault_generator = SoftwareFaultGenerator(endpoint)
            background_tasks.add_coroutine(fault_generator.run())

        logging.info(f"Starting {profile.vendor}...")
        background_tasks.add_coroutine(
            profile.vendor.run(endpoint), label=f"{profile.vendor.name}"
        )

        remaining_time = profile.stop_time - get_server_datetime()
        logging.info(f"Benchmarking for {remaining_time}...")
        await background_tasks.run_for(remaining_time)

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

    handler.uninstall()

    return profile


async def synchronize_time_ntp(local_machine: Machine):
    # Synchronize the time to NTP
    logging.info(f"Starting initial time synchronization via Chrony.")
    ntp = VendorDB.CHRONY
    await ntp.initial_time_synchronization()

async def clock_jump(local_machine: Machine, use_initial_clock_offset: bool = True):
    # Step the clock using PPSi tool
    target_clock_offset = local_machine.initial_clock_offset if use_initial_clock_offset else None
    if target_clock_offset is not None:
        logging.info(f"Adjusting node {local_machine} time by {target_clock_offset}.")
        await Invocation.of_command(
            "lib/ppsi/tools/jmptime", str(target_clock_offset.total_seconds())
        ).as_privileged().set_working_directory(PTPPERF_REPOSITORY_ROOT).run()
    logging.info(f"{local_machine} time is now {datetime.now()}")
