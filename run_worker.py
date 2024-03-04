import asyncio
from argparse import ArgumentParser

from ptp_perf import util
from ptp_perf.utilities.django import bootstrap_django_environment

if __name__ == '__main__':
    util.setup_logging()

    # This proxy program is necessary so that the client is start from the root of the python project and no messing with the PYTHONPATH is necessary.
    parser = ArgumentParser(
        description="Client program that executes PTP-Perf functions on behalf of the orchestrator. "
                    "This program should not be run by the user, it is invoked by the orchestrator. "
                    "Connects to the orchestrator via the django database."
    )
    parser.add_argument("--endpoint-id", type=str, required=True, help="The endpoint ID of the PTP profile to run.")

    result = parser.parse_args()
    endpoint_id = result.endpoint_id

    with util.StackTraceGuard():
        bootstrap_django_environment()

        from ptp_perf import benchmark
        asyncio.run(benchmark.benchmark(endpoint_id=endpoint_id))
