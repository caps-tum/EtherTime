import asyncio
import copy
import logging
from argparse import ArgumentParser
from datetime import datetime, timedelta
from typing import List

import config
import util
from cluster_restart import restart_cluster
from machine import Cluster
from profiles.base_profile import BaseProfile, ProfileType
from profiles.benchmark import Benchmark
from registry.benchmark_db import BenchmarkDB
from rpc.server import RPCServer
from rpc.server_service import RPCServerService
from util import StackTraceGuard, str_join
from vendor.registry import VendorDB
from vendor.vendor import Vendor


async def do_benchmark(rpc_server: RPCServer, cluster: Cluster, benchmark: Benchmark, vendor: Vendor):
    profile_timestamp = datetime.now()
    profile_template = BaseProfile(
        id=f"{BaseProfile.format_id_timestamp(timestamp=profile_timestamp)}",
        benchmark=benchmark,
        machine_id=None,
        profile_type=ProfileType.RAW,
        vendor_id=vendor.id,
        start_time=profile_timestamp,
    )

    profiles: List[str] = await util.async_gather_with_progress(*[
        rpc_server.remote_function_run_as_async(
            rpc_server.get_remote_service(machine.id).benchmark,
            profile_template.dump()
        ) for machine in cluster.machines
    ], label="Benchmarking...")

    for json in profiles:
        profile = BaseProfile.load_str(json)
        print(f"Saving profile to {profile.file_path_relative}")
        profile.save()


async def run_orchestration(benchmarks: List[str], vendors: List[str],
                            num_iterations: int = 1, duration_override: timedelta = None, test_mode: bool = False):
    configuration = config.current_configuration
    cluster = configuration.cluster

    if not test_mode:
        await restart_cluster(cluster)
    else:
        logging.info("Skipping cluster restart due to test mode.")

    if test_mode and duration_override is None:
        duration_override = timedelta(minutes=1)
        logging.info(f"Applying duration override of {duration_override} due to test mode.")

    RPCServer.service_type = RPCServerService
    rpc_server = RPCServer()
    try:
        rpc_server.start_rpc_server()
        await rpc_server.start_remote_clients(cluster.machines)
        await rpc_server.wait_for_clients_connected()

        for iteration in range(num_iterations):
            logging.info(f"Iteration {iteration+1}/{num_iterations}.")
            logging.info(f"Running {len(benchmarks)} benchmarks ({str_join(benchmarks)}) on {len(vendors)} vendors ({str_join(vendors)})")

            for benchmark_id in benchmarks:
                for vendor in vendors:
                    benchmark = BenchmarkDB.get(benchmark_id)
                    if duration_override:
                        benchmark = copy.deepcopy(benchmark)
                        benchmark.duration = duration_override
                        logging.info(f"Applied benchmark duration override: {benchmark.duration}")

                    logging.info(f"Now running benchmark: {benchmark_id} for vendor {vendor}")
                    try:
                        await do_benchmark(
                            rpc_server, cluster,
                            benchmark=benchmark, vendor=VendorDB.get(vendor)
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
        "--benchmark", choices=BenchmarkDB.all_by_id().keys(), action='append', default=[],
        help="Specify which benchmark configuration to run, can be specified multiple times."
    )
    parser.add_argument(
        "--benchmark-regex", type=str, default=None,
        help="Select benchmarks based off of a regex applied to their ids."
    )
    parser.add_argument(
        "--vendor", choices=[vendor.id for vendor in VendorDB.all()], action='append', default=[], required=True,
        help="Specify which vendor to benchmark, can be specified multiple times."
    )
    parser.add_argument(
        "--iterations", "-i", type=int, default=1, help="Number of times to run the benchmark."
    )
    parser.add_argument(
        "--duration", type=int, default=None, help="Duration override (in minutes)",
    )
    parser.add_argument(
        "--test", action="store_true", default=False, help="Run this benchmark in test mode (1 minute, no restart)"
    )

    result = parser.parse_args()

    benchmarks: List[str] = result.benchmark
    if result.benchmark_regex:
        benchmarks += [benchmark.id for benchmark in BenchmarkDB.get_by_regex(regex=result.benchmark_regex)]
    duration_override = None
    if result.duration is not None:
        duration_override = timedelta(minutes=result.duration)

    test_mode = result.test

    with StackTraceGuard():
        asyncio.run(run_orchestration(
            benchmarks=benchmarks, vendors=result.vendor,
            num_iterations=result.iterations, duration_override=duration_override, test_mode=test_mode
        ))
