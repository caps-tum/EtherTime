import asyncio
import logging
import time
from argparse import ArgumentParser
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ptp_perf.constants import LOCAL_DIR, ensure_directory_exists
from ptp_perf.invoke.invocation import Invocation, InvocationFailedException
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.util import PathOrStr, setup_logging, StackTraceGuard
from ptp_perf.utilities.pydantic import pydantic_save_model, pydantic_load_model
from ptp_perf.vendor.registry import VendorDB

QUEUE = ensure_directory_exists(LOCAL_DIR.joinpath("task_queue"))
QUEUE_FILE = QUEUE.joinpath("task_queue.json")


@dataclass
class ScheduleTask:
    name: str
    command: str
    estimated_time: timedelta

    id: Optional[int] = None
    slack_time: Optional[timedelta] = field(default_factory=lambda: timedelta(minutes=5))
    success: Optional[bool] = None
    start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None

    def run(self):
        self.start_time = datetime.now()
        self.save(self.get_file_path(self.id, pending=True))
        try:
            invocation = Invocation.of_shell(command=self.command)
            asyncio.run(invocation.run(timeout=self.timeout.total_seconds()))
            self.success = True
        except InvocationFailedException as e:
            logging.exception("Failed to run task", exc_info=e)
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

    @property
    def estimated_time_remaining(self) -> timedelta:
        """Estimated task time remaining, based off of whether the task is started."""
        return self.estimated_time if not self.running else max(timedelta(minutes=0), self.estimated_time - (datetime.now() - self.start_time))

    @property
    def running(self) -> bool:
        return self.start_time is not None

    @property
    def timeout(self):
        if self.estimated_time is None or self.slack_time is None:
            return None
        return self.estimated_time + self.slack_time

    def __str__(self):
        return f"{self.name} ({self.id})"


@dataclass
class ScheduleQueue:
    paused: bool = False

    @staticmethod
    def load() -> "ScheduleQueue":
        try:
            return pydantic_load_model(ScheduleQueue, QUEUE_FILE)
        except FileNotFoundError:
            new_queue = ScheduleQueue()
            new_queue.save()
            return new_queue

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
    def queue_task(task: ScheduleTask):
        task.id = len(list(QUEUE.iterdir()))
        task.save(ScheduleTask.get_file_path(task.id, pending=True))
        logging.info(f"Scheduled task {task.id}: {task} ")


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
    name = result.name
    command = result.command
    estimated_time = result.time
    ScheduleQueue.queue_task(
        ScheduleTask(
            name=name,
            command=command,
            estimated_time=timedelta(minutes=estimated_time),
        )
    )


def info(result):
    alignment_str = "{0: >4}  {1: <50}  {2: >20}  {3: >20}"

    now = datetime.now().replace(microsecond=0)
    eta = now
    print(alignment_str.format("Id", "Name", "Est. Time Remaining", "ETA"))
    pending_task_paths = ScheduleQueue.load().pending_task_paths()
    for task_path in pending_task_paths:
        task = ScheduleTask.load(task_path)

        remaining_time = task.estimated_time_remaining

        eta = eta + remaining_time
        timedelta()
        print(alignment_str.format(task.id, task.name + (" (running)" if task.running else ''), str(remaining_time).split(".")[0], str(eta.strftime("%H:%M"))))

    remaining_duration = eta.replace(microsecond=0) - now.replace(microsecond=0)
    print(f"Estimated completion of {len(pending_task_paths)} tasks in {remaining_duration}")


def queue_benchmarks(result):
    regex = result.benchmark_regex
    benchmarks = BenchmarkDB.get_by_regex(regex)
    vendors = result.vendor
    if result.duration is not None:
        duration_override = timedelta(minutes=result.duration)
    else:
        duration_override = None
    test_mode = result.test
    analyze = result.analyze

    if len(vendors) == 0:
        vendors = VendorDB.ANALYZED_VENDORS
    else:
        vendors = [VendorDB.get(vendor_id) for vendor_id in vendors]

    for benchmark in benchmarks:
        for vendor in vendors:
            command = f"LOG_EXCEPTIONS=1 python3 run_orchestration.py --benchmark '{benchmark.id}' --vendor {vendor.id}"

            if duration_override is None:
                duration = benchmark.duration
            else:
                duration = duration_override
                command += f" --duration {int(duration.total_seconds() // 60)}"

            if test_mode:
                command += " --test"

            if analyze:
                command += " --analyze"

            ScheduleQueue.queue_task(
                ScheduleTask(
                    name=f"{benchmark.name} ({vendor.name})",
                    command=command,
                    estimated_time=duration,
                )
            )


def pause_queue(result):
    should_pause = not result.unpause

    queue = ScheduleQueue.load()
    queue.paused = should_pause
    queue.save()
    print(
        (f"Paused" if queue.paused else "Unpaused") + f" the queue ({len(queue.pending_task_paths())} tasks pending).")

