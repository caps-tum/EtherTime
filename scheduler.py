from argparse import ArgumentParser

from ptp_perf.utilities.django_utilities import bootstrap_django_environment
bootstrap_django_environment()

from ptp_perf.scheduler import run_scheduler, queue_task, queue_benchmarks, info
from ptp_perf.util import setup_logging, StackTraceGuard

if __name__ == '__main__':
    setup_logging()
    parser = ArgumentParser(description="Batch processing for PTP-Perf.")
    subparsers = parser.add_subparsers(required=True)

    run_command = subparsers.add_parser("run", help="Run the batch processing queue.")
    run_command.set_defaults(action=run_scheduler)

    queue_command = subparsers.add_parser("queue", help="Add a task to the task queue.")
    queue_command.set_defaults(action=queue_task)
    queue_command.add_argument("--name", type=str, required=True, help="A name for the task.")
    queue_command.add_argument("--command", type=str, required=True, help="The command to run.")
    queue_command.add_argument("--time", type=int, default=None, help="The estimated task time in minutes. A slack time of 5 minutes is added as a timeout.")

    queue_benchmarks_command = subparsers.add_parser("queue-benchmarks",
                                                     help="Queue benchmarks by filtering with regex")
    queue_benchmarks_command.set_defaults(action=queue_benchmarks)
    queue_benchmarks_command.add_argument("--benchmark-regex", type=str, required=True,
                                          help="RegEx for filtering benchmark ids.")
    queue_benchmarks_command.add_argument("--vendor", action='append', default=[],
                                          help="Vendors to benchmark (default all). Can be specified multiple times.")
    queue_benchmarks_command.add_argument("--cluster", action='append', default=[],
                                          help="Which cluster to run the benchmark on, by cluster id. Can be specified multiple times.")
    queue_benchmarks_command.add_argument("--target-count", type=int, default=None,
                                          help="The number of profiles to target (queues as many as necessary to reach the target count).")
    queue_benchmarks_command.add_argument("--duration", type=int, default=None, help="Duration override (in minutes)")
    queue_benchmarks_command.add_argument("--test", action="store_true", default=False, help="Run this benchmark in test mode.")
    queue_benchmarks_command.add_argument("--analyze", action="store_true", default=False, help="Analyze the profile after benchmarking.")

    info_command = subparsers.add_parser("info", help="Retrieve queue status.")
    info_command.set_defaults(action=info)

    result = parser.parse_args()

    with StackTraceGuard():
        result.action(result)
