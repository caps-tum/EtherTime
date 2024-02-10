import asyncio
import logging
import re
from argparse import ArgumentParser
from datetime import datetime
from typing import List

import config
import util
from constants import MEASUREMENTS_DIR
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
        id=f"{benchmark.id}-{BaseProfile.format_id_timestamp(timestamp=profile_timestamp)}",
        benchmark=benchmark,
        machine_id=None,
        profile_type=ProfileType.RAW,
        vendor_id=vendor.id,
        start_time=profile_timestamp,
    )

    logging.info("Preparing machines...")
    await util.async_gather_with_progress(*[
        rpc_server.remote_function_run_as_async(
            rpc_server.get_remote_service(machine.id).prepare
        ) for machine in cluster.machines
    ], label="Preparing system...")

    profiles: List[str] = await util.async_gather_with_progress(*[
        rpc_server.remote_function_run_as_async(
            rpc_server.get_remote_service(machine.id).benchmark,
            profile_template.dump()
        ) for machine in cluster.machines
    ], label="Benchmarking...")

    for json in profiles:
        profile = BaseProfile.load_str(json)
        output_location = MEASUREMENTS_DIR.joinpath(profile.filename)
        print(f"Saving profile to {output_location}")
        profile.save(output_location)


async def run_orchestration(benchmarks: List[str], vendors: List[str]):
    configuration = config.current_configuration
    cluster = configuration.cluster

    logging.info(f"Running {len(benchmarks)} benchmarks ({str_join(benchmarks)}) on {len(vendors)} vendors ({str_join(vendors)})")

    RPCServer.service_type = RPCServerService
    rpc_server = RPCServer()
    try:
        rpc_server.start_rpc_server()
        await rpc_server.start_remote_clients(cluster.machines)
        await rpc_server.wait_for_clients_connected()

        for benchmark in benchmarks:
            for vendor in vendors:
                logging.info(f"Now running benchmark: {benchmark} for vendor {vendor}")
                try:
                    await do_benchmark(
                        rpc_server, cluster,
                        benchmark=BenchmarkDB.get(benchmark), vendor=VendorDB.get(vendor)
                    )
                except Exception as e:
                    util.log_exception(e)

    finally:
        rpc_server.stop_rpc_server()


if __name__ == '__main__':
    util.setup_logging()

    parser = ArgumentParser(description="Program to run PTP-Perf benchmarks")
    parser.add_argument(
        "--benchmark", choices=BenchmarkDB.all_by_id().keys(), action='append', default=[], required=True,
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

    result = parser.parse_args()

    benchmarks = result.benchmark
    if result.benchmark_regex:
        benchmarks += [benchmark for benchmark in BenchmarkDB.all() if re.match(result.benchmark_regex, benchmark.id)]

    with StackTraceGuard():
        asyncio.run(run_orchestration(benchmarks=benchmarks, vendors=result.vendor))
