import asyncio
import copy
import logging
from argparse import ArgumentParser
from datetime import datetime, timedelta
from typing import List

import config
from adapters.device_control import DeviceControl
from config import Configuration
import util
from cluster_restart import restart_cluster
from profiles.base_profile import BaseProfile, ProfileType
from profiles.benchmark import Benchmark
from registry.benchmark_db import BenchmarkDB
from rpc.server import RPCServer
from rpc.server_service import RPCServerService
from util import StackTraceGuard
from utilities.multi_task_controller import MultiTaskController
from vendor.registry import VendorDB
from vendor.vendor import Vendor


async def do_benchmark(rpc_server: RPCServer, configuration: Configuration, benchmark: Benchmark, vendor: Vendor):
    profile_timestamp = datetime.now()
    profile_template = BaseProfile(
        id=f"{BaseProfile.format_id_timestamp(timestamp=profile_timestamp)}",
        benchmark=benchmark,
        machine_id=None,
        profile_type=ProfileType.RAW,
        vendor_id=vendor.id,
        start_time=profile_timestamp,
        configuration=configuration,
    )

    controller = MultiTaskController()

    try:
        if benchmark.fault_tolerance_hardware_fault_interval is not None:
            device_controller = DeviceControl(profile_template)
            controller.add_coroutine(
                device_controller.run()
            )

        profiles: List[str] = await util.async_gather_with_progress(*[
            rpc_server.remote_function_run_as_async(
                rpc_server.get_remote_service(machine.id).benchmark,
                profile_template.dump()
            ) for machine in configuration.cluster.machines
        ], label="Benchmarking...")

        for json in profiles:
            profile = BaseProfile.load_str(json)

            # Merge raw_data on orchestrator into raw_data on client
            profile.raw_data.update(profile_template.raw_data)

            print(f"Saving profile to {profile.file_path_relative}")
            profile.save()

    finally:
        await controller.cancel_pending_tasks()


async def run_orchestration(benchmark_id: str, vendor_id: str,
                            duration_override: timedelta = None, test_mode: bool = False):

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
        try:
            await do_benchmark(
                rpc_server, configuration,
                benchmark=benchmark, vendor=vendor
            )
        except Exception as e:
            util.log_exception(e)
    except Exception as e:
        util.log_exception(e)
    finally:
        await rpc_server.stop_rpc_server()


if __name__ == '__main__':
    util.setup_logging()

    parser = ArgumentParser(description="Program to run PTP-Perf benchmarks")
    parser.add_argument(
        "--benchmark", choices=BenchmarkDB.all_by_id().keys(), required=True,
        help="Specify which benchmark to run, by benchmark id."
    )
    parser.add_argument(
        "--vendor", choices=[vendor.id for vendor in VendorDB.all()], required=True,
        help="Specify which vendor to benchmark, by vendor id."
    )
    parser.add_argument(
        "--duration", type=int, default=None, help="Duration override (in minutes)",
    )
    parser.add_argument(
        "--test", action="store_true", default=False, help="Run this benchmark in test mode (1 minute, no restart)"
    )

    result = parser.parse_args()

    duration_override = None
    if result.duration is not None:
        duration_override = timedelta(minutes=result.duration)

    test_mode = result.test

    with StackTraceGuard():
        asyncio.run(run_orchestration(
            benchmark_id=result.benchmark, vendor_id=result.vendor,
            duration_override=duration_override, test_mode=test_mode
        ))
