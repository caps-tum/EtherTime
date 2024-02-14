import asyncio
import logging
import time
from argparse import ArgumentParser
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from pydantic import RootModel

from constants import LOCAL_DIR, ensure_directory_exists
from invoke.invocation import Invocation, InvocationFailedException
from registry.benchmark_db import BenchmarkDB
from util import PathOrStr, setup_logging, StackTraceGuard
from vendor.registry import VendorDB

QUEUE = ensure_directory_exists(LOCAL_DIR.joinpath("task_queue"))
QUEUE_FILE = QUEUE.joinpath("task_queue.json")


def pydantic_save_model(model, instance, path: PathOrStr):
    Path(path).write_text(RootModel[model](instance).model_dump_json(indent=4))

def pydantic_load_model(model, path: PathOrStr):
    return RootModel[model].model_validate_json(Path(path).read_text()).root


@dataclass
class ScheduleTask:
    id: int
    command: str
    timeout: Optional[timedelta] = None
    success: Optional[bool] = None
    start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None

    def run(self):
        self.start_time = datetime.now()
        try:
            invocation = Invocation.of_shell(command=self.command)
            asyncio.run(invocation.run(timeout=self.timeout.total_seconds()))
            self.success = True
        except InvocationFailedException:
            self.success = False
        self.completion_time = datetime.now()
        logging.info(f"Task {self.id} completed at {self.completion_time} (success: {self.success}).")

        self.save(self.get_file_path(self.id, pending=False))
        self.get_file_path(self.id, pending=True).unlink()

    @property
    def completed(self):
        return self.success is not None

    @staticmethod
    def get_file_path(task_id: int, pending: bool) -> Path:
        return QUEUE.joinpath(f"task_{task_id:04d}_{'pending' if pending else 'complete'}.json")

    @staticmethod
    def load(path: PathOrStr) -> "ScheduleTask":
        return pydantic_load_model(ScheduleTask, path)

    def save(self, path: PathOrStr):
        pydantic_save_model(ScheduleTask, self, path)


    def __str__(self):
        return f"Task {self.id} ({self.command})"


@dataclass
class ScheduleQueue:
    paused: bool = False

    @staticmethod
    def load() -> "ScheduleQueue":
        try:
            return pydantic_load_model(ScheduleQueue, QUEUE_FILE)
        except FileNotFoundError:
            return ScheduleQueue()

    def save(self):
        pydantic_save_model(ScheduleQueue, self, QUEUE_FILE)

    def next_task(self) -> Optional[ScheduleTask]:
        pending_tasks = self.pending_task_paths()
        if len(pending_tasks) == 0:
            return None
        return ScheduleTask.load(pending_tasks[0])

    def pending_task_paths(self):
        return sorted(QUEUE.glob("task_*_pending.json"))

    @staticmethod
    def queue_task(command: str, timeout: float):
        task = ScheduleTask(
            id=len(list(QUEUE.iterdir())),
            command=command,
            timeout=timedelta(seconds=timeout),
        )
        task.save(ScheduleTask.get_file_path(task.id, pending=True))
        logging.info(f"Scheduled task {task.id} with command '{command}'")


def run_scheduler(result):
    while True:
        queue = ScheduleQueue.load()

        if queue.paused:
            time.sleep(5)
            continue

        task = queue.next_task()
        if task is not None:
            logging.info(f"Running task: {task}")
            task.run()


def queue_task(result):
    command = result.command
    timeout = result.timeout
    ScheduleQueue.queue_task(command, timeout)


def info(result):
    alignment_str = "{0: >4}  {1: <50}  {2: >12}  {3: >20}"

    now = datetime.now().replace(microsecond=0)
    eta = now
    print(alignment_str.format("Id", "Command", "Timeout", "ETA"))
    for task_path in ScheduleQueue.load().pending_task_paths():
        task = ScheduleTask.load(task_path)

        eta = eta + (task.timeout if task.timeout else 0)
        print(alignment_str.format(task.id, task.command, str(task.timeout), str(eta.strftime("%H:%M"))))

    print(f"Estimated queue duration: {eta - now}")

def queue_benchmarks(result):
    regex = result.benchmark_regex
    benchmarks = BenchmarkDB.get_by_regex(regex)
    vendors = result.vendor
    if len(vendors) == 0:
        vendors = VendorDB.ANALYZED_VENDORS
    else:
        vendors = [VendorDB.get(vendor_id) for vendor_id in vendors]

    for benchmark in benchmarks:
        for vendor in vendors:
            ScheduleQueue.queue_task(
                'for host in rpi06 rpi08; do ssh "$host" sudo killall ptpd ptp4l phc2sys iperf stress-ng python3; done;',
                timeout=60,
            )

            ScheduleQueue.queue_task(
                f"LOG_EXCEPTIONS=1 python3 orchestrator.py --benchmark '{benchmark.id}' --vendor {vendor.id}",
                timeout=(benchmark.duration + timedelta(minutes=5)).total_seconds(),
            )


if __name__ == '__main__':
    setup_logging()
    parser = ArgumentParser(description="Batch processing for PTP-Perf.")
    subparsers = parser.add_subparsers(required=True)

    run_command = subparsers.add_parser("run", help="Run the batch processing queue.")
    run_command.set_defaults(action=run_scheduler)

    queue_command = subparsers.add_parser("queue", help="Add a task to the task queue.")
    queue_command.set_defaults(action=queue_task)
    queue_command.add_argument("--command", type=str, required=True, help="The command to run.")
    queue_command.add_argument("--timeout", type=int, default=None, help="The maximum task duration in seconds.")

    queue_benchmarks_command = subparsers.add_parser("queue-benchmarks", help="Queue benchmarks by filtering with regex")
    queue_benchmarks_command.set_defaults(action=queue_benchmarks)
    queue_benchmarks_command.add_argument("--benchmark-regex", type=str, required=True, help="RegEx for filtering benchmark ids.")
    queue_benchmarks_command.add_argument("--vendor", action='append', default=[], help="Vendors to benchmark (default all). Can be specified multiple times.")

    info_command = subparsers.add_parser("info", help="Retrieve queue status.")
    info_command.set_defaults(action=info)

    result = parser.parse_args()

    with StackTraceGuard():
        result.action(result)
