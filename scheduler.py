from argparse import ArgumentParser

from ptp_perf.utilities.django_utilities import bootstrap_django_environment
bootstrap_django_environment()

from ptp_perf.scheduler import run_scheduler, queue_task, queue_benchmarks, info, available_benchmarks
from ptp_perf.util import setup_logging, StackTraceGuard

if __name__ == '__main__':
    setup_logging()
    parser = ArgumentParser(description="Batch processing for PTP-Perf.")
    subparsers = parser.add_subparsers(required=True)

    run_command = subparsers.add_parser(
        "run",
        help="Run the scheduler to process tasks in the queue. "
             "Tasks are processed in priority order, only one task is processed at a time. "
             "The scheduler will run indefinitely until stopped."
    )
    run_command.set_defaults(action=run_scheduler)

    queue_command = subparsers.add_parser(
        "queue",
        help="Add a single task to the task queue. "
             "A task is a command to run on the orchestrator. "
             "The tasks will be executed in the order it was queued. "
             "The time parameter limits the task execution time, after which the task is considered failed."
    )
    queue_command.set_defaults(action=queue_task)
    queue_command.add_argument("--name", type=str, required=True, help="A name for the task.")
    queue_command.add_argument("--command", type=str, required=True, help="The shell command to run.")
    queue_command.add_argument("--time", type=int, default=None, help="The estimated task time in minutes. A slack time of 5 minutes is added as a timeout.")

    queue_benchmarks_command = subparsers.add_parser(
        "queue-benchmarks",
         help="Queue multiple benchmarks by filtering with regex. "
              "Each benchmark which matches the regex will be queued as a separate task. "
              "If vendor is specified, only benchmarks from that vendor will be queued. Otherwise, all vendors will be queued. "
              "If cluster is specified, only benchmarks from that cluster will be queued. Otherwise, all clusters will be queued. "
              "The target count parameter queues as many benchmarks as necessary to reach the target number of profiles for that benchmark. "
              "E.g., if you want to queue 10 profiles of the baseline benchmark, and there are already 5 profiles, 5 more will be queued."
    )
    queue_benchmarks_command.set_defaults(action=queue_benchmarks)
    queue_benchmarks_command.add_argument("--benchmark-regex", type=str, required=True,
                                          help="RegEx for filtering benchmark ids.")
    queue_benchmarks_command.add_argument("--vendor", action='append', default=[],
                                          help="Vendors to benchmark (default all). Can be specified multiple times.")
    queue_benchmarks_command.add_argument("--cluster", action='append', default=[],
                                          help="Which cluster to run the benchmark on (default all), by cluster id. Can be specified multiple times.")
    queue_benchmarks_command.add_argument("--target-count", type=int, default=None,
                                          help="The number of profiles to target (queues as many as necessary to reach the target count).")
    queue_benchmarks_command.add_argument("--priority", type=int, default=0,
                                          help="The priority to assign to scheduled tasks. Higher priority tasks are executed first.")
    queue_benchmarks_command.add_argument("--add-pause", action='store_true',
                                          help="Add a pause after the scheduled tasks finish. The runner needs to be resumed manually.")
    queue_benchmarks_command.add_argument("--duration", type=int, default=None, help="Duration override of the benchmark to run in minutes.")
    queue_benchmarks_command.add_argument("--test", action="store_true", default=False, help="Run this benchmark in test mode. This will run the benchmark with a reduced duration and certain steps like restarting the nodes before benchmarking are skipped.")
    queue_benchmarks_command.add_argument("--analyze", action="store_true", default=False, help="Analyze the profile after benchmarking. This will parse the logs and generate summary statistics and timeseries data.")

    info_command = subparsers.add_parser("info", help="Retrieve queue status. This will show the current queue status and the number of tasks in the queue, as well as the estimated time to completion.")
    info_command.set_defaults(action=info)

    available_command = subparsers.add_parser("available", help="List available benchmarks and their descriptions.")
    available_command.set_defaults(action=available_benchmarks)

    result = parser.parse_args()

    with StackTraceGuard():
        result.action(result)
