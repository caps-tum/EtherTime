import asyncio
import copy
import logging
import os
from argparse import ArgumentParser
from datetime import datetime, timedelta

from ptp_perf import config
from ptp_perf import util
from ptp_perf.adapters.device_control import DeviceControl
from ptp_perf.analyze import convert_profile
from ptp_perf.cluster_restart import restart_cluster
from ptp_perf.config import Configuration
from ptp_perf.profiles.benchmark import Benchmark
from ptp_perf.models import PTPProfile, PTPEndpoint
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.rpc.server import RPCServer
from ptp_perf.rpc.server_service import RPCServerService
from ptp_perf.util import StackTraceGuard, str_join
from ptp_perf.utilities.multi_task_controller import MultiTaskController
from ptp_perf.vendor.registry import VendorDB
from ptp_perf.vendor.vendor import Vendor


async def do_benchmark(rpc_server: RPCServer, configuration: Configuration, benchmark: Benchmark, vendor: Vendor) -> PTPProfile:

    profile_timestamp = datetime.now()
    profile = PTPProfile(
        benchmark_id=benchmark.id,
        vendor_id=vendor.id,
        state=PTPProfile.ProfileState.RUNNING,
        start_time=profile_timestamp,
        stop_time=profile_timestamp + benchmark.duration
    )
    profile.save()

    orchestrator_endpoint = PTPEndpoint(
        profile=profile,
        machine_id="orchestrator",
    )

    controller = MultiTaskController()

    try:
        if benchmark.fault_tolerance_hardware_fault_interval is not None:
            device_controller = DeviceControl(orchestrator_endpoint)
            controller.add_coroutine(
                device_controller.run()
            )

        for machine in configuration.cluster.machines:
            controller.add_coroutine(
                rpc_server.remote_function_run_as_async(
                    rpc_server.get_remote_service(machine.id).benchmark,
                    profile_template.dump()
                )
            )

        # Wait until the first exit, then give some more time for others to exit.
        # If the others don't exit in time, they will be cancelled
        await controller.run_for()
        await controller.run_for(duration=timedelta(seconds=10), wait_for_all=True)

    finally:
        await controller.cancel_pending_tasks()

        profile.state = PTPProfile.ProfileState.VALID
        profile.save()

    return profile

async def run_orchestration(benchmark_id: str, vendor_id: str,
                            duration_override: timedelta = None, test_mode: bool = False, analyze: bool = False):
    benchmark = BenchmarkDB.get(benchmark_id)
    vendor = VendorDB.get(vendor_id)

    configuration = config.subset_cluster(
        config.get_configuration_by_cluster_name("Pi Cluster"),
        benchmark.num_machines,
    )

    if not test_mode:
        await restart_cluster(configuration.cluster)
    else:
        logging.info("Skipping cluster restart due to test mode.")

    if test_mode and duration_override is None:
        duration_override = timedelta(minutes=1)
        logging.info(f"Applying duration override of {duration_override} due to test mode.")

    RPCServer.service_type = RPCServerService
    rpc_server = RPCServer()
    try:
        rpc_server.start_rpc_server()
        await rpc_server.start_remote_clients(configuration.cluster.machines)
        await rpc_server.wait_for_clients_connected()

        if duration_override:
            benchmark = copy.deepcopy(benchmark)
            benchmark.duration = duration_override
            logging.info(f"Applied benchmark duration override: {benchmark.duration}")

        logging.info(f"Now running benchmark: {benchmark_id} for vendor {vendor_id}")
        profiles = await do_benchmark(
            rpc_server, configuration,
            benchmark=benchmark, vendor=vendor
        )

        if analyze:
            logging.info(f"Analyzing profiles: {str_join(profiles)}")
            for profile in profiles:
                convert_profile(profile)
    except Exception as e:
        util.log_exception(e)
    finally:
        await rpc_server.stop_rpc_server()
