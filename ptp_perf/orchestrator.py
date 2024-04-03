import copy
import copy
import logging
from datetime import datetime, timedelta

from ptp_perf import config
from ptp_perf import util
from ptp_perf.adapters.device_control import DeviceControl
from ptp_perf.cluster_restart import restart_cluster
from ptp_perf.config import Configuration
from ptp_perf.invoke.invocation import Invocation
from ptp_perf.models import PTPProfile, PTPEndpoint
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.profiles.benchmark import Benchmark
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.util import str_join
from ptp_perf.utilities.logging import LogToDBLogRecordHandler
from ptp_perf.utilities.multi_task_controller import MultiTaskController
from ptp_perf.vendor.registry import VendorDB
from ptp_perf.vendor.vendor import Vendor


async def do_benchmark(configuration: Configuration, benchmark: Benchmark, vendor: Vendor) -> PTPProfile:

    profile_timestamp = datetime.now().astimezone()
    profile = PTPProfile(
        benchmark_id=benchmark.id,
        vendor_id=vendor.id,
        cluster_id=configuration.cluster.id,
        is_running=True,
        start_time=profile_timestamp,
        stop_time=profile_timestamp + benchmark.duration
    )
    await profile.asave()

    orchestrator_endpoint = PTPEndpoint(
        profile=profile,
        machine_id="orchestrator",
        endpoint_type=EndpointType.ORCHESTRATOR,
    )
    await orchestrator_endpoint.asave()

    logging_handler = LogToDBLogRecordHandler(orchestrator_endpoint)
    logging_handler.install()

    controller = MultiTaskController()

    try:

        for machine in configuration.cluster.machines:
            machine_endpoint = PTPEndpoint(
                profile=profile,
                machine_id=machine.id,
                endpoint_type=machine.endpoint_type,
            )
            await machine_endpoint.asave()

            machine._ssh_session = Invocation.of_command(
                "ssh", machine.address,
                "-o", "ServerAliveInterval=3", "-o", "ServerAliveCountMax=3",
                "-o", "ConnectTimeout=5", "-o", "ConnectionAttempts=1",
                f"cd '{machine.remote_root}/' && "
                f"LOG_EXCEPTIONS=1 python3 run_worker.py --endpoint-id {machine_endpoint.id}"
            )
            controller.add_coroutine(
                machine._ssh_session.run(), label=f"Orchestrator remote session {machine_endpoint.machine_id}"
            )

        if benchmark.fault_hardware:
            device_controller = DeviceControl(orchestrator_endpoint, configuration)
            controller.add_coroutine(device_controller.run(), label="Hardware Fault Controller")


        # Wait until the first exit, then give some more time for others to exit.
        # If the others don't exit in time, they will be cancelled
        await controller.run_for()
        await controller.run_for(duration=timedelta(seconds=10), wait_for_all=True)

    finally:
        await controller.cancel_pending_tasks()

        profile.is_running = False
        await profile.asave()

    logging_handler.uninstall()

    return profile

async def run_orchestration(benchmark_id: str, vendor_id: str,
                            duration_override: timedelta = None, test_mode: bool = False, analyze: bool = False):
    benchmark = BenchmarkDB.get(benchmark_id)
    vendor = VendorDB.get(vendor_id)

    configuration = config.subset_cluster(
        config.get_configuration_by_cluster_name("Pi Cluster"),
        benchmark.num_machines,
    )
    await configuration.cluster.synchronize_repositories()

    if not test_mode:
        await restart_cluster(configuration.cluster)
    else:
        logging.info("Skipping cluster restart due to test mode.")

    if test_mode and duration_override is None:
        duration_override = timedelta(minutes=1)
        logging.info(f"Applying duration override of {duration_override} due to test mode.")

    if duration_override:
        benchmark = copy.deepcopy(benchmark)
        benchmark.duration = duration_override
        logging.info(f"Applied benchmark duration override: {benchmark.duration}")

    logging.info(f"Now running benchmark: {benchmark_id} for vendor {vendor_id}")
    await do_benchmark(
        configuration,
        benchmark=benchmark, vendor=vendor
    )
