import asyncio
from argparse import ArgumentParser
from datetime import timedelta

from ptp_perf.utilities.django_utilities import bootstrap_django_environment
bootstrap_django_environment()

from ptp_perf import util, config
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.util import StackTraceGuard
from ptp_perf.vendor.registry import VendorDB

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
        "--cluster", choices=config.clusters.keys(), required=True,
        help="Specify which cluster to benchmark on, by cluster id."
    )
    parser.add_argument(
        "--duration", type=int, default=None, help="Duration override (in minutes)",
    )
    parser.add_argument(
        "--test", action="store_true", default=False, help="Run this benchmark in test mode (1 minute, no restart)"
    )
    parser.add_argument(
        "--analyze", action='store_true', default=False,
        help="Analyze the benchmark profile after running the benchmark."
    )

    result = parser.parse_args()

    duration_override = None
    if result.duration is not None:
        duration_override = timedelta(minutes=result.duration)

    test_mode = result.test

    with StackTraceGuard():

        from ptp_perf.orchestrator import run_orchestration

        asyncio.run(run_orchestration(
            benchmark_id=result.benchmark, vendor_id=result.vendor, cluster_id=result.cluster,
            duration_override=duration_override, test_mode=test_mode,
        ))
