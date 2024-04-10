import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from django.utils import timezone

from ptp_perf import config
from ptp_perf.constants import LOCAL_DIR, ensure_directory_exists
from ptp_perf.models.schedule_task import ScheduleTask
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.vendor.registry import VendorDB

QUEUE = ensure_directory_exists(LOCAL_DIR.joinpath("task_queue"))
QUEUE_FILE = QUEUE.joinpath("task_queue.json")

@dataclass
class ScheduleQueue:

    @staticmethod
    def next_task() -> Optional[ScheduleTask]:
        pending_tasks = ScheduleQueue.pending_tasks()

        try:
            return pending_tasks.first()
        except ScheduleTask.DoesNotExist:
            return None

    @staticmethod
    def pending_tasks():
        return ScheduleTask.objects.filter(completion_time__isnull=True)

    @staticmethod
    def queue_task(task: ScheduleTask):
        task.save()
        logging.info(f"Scheduled task {task.id}: {task} ")


def run_scheduler(result):
    while True:

        task = ScheduleQueue.next_task()
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

    now = timezone.now().replace(microsecond=0)
    eta = now
    print(alignment_str.format("Id", "Name", "Est. Time Remaining", "ETA"))
    pending_tasks = ScheduleQueue.pending_tasks()
    for task in pending_tasks:
        remaining_time = task.estimated_time_remaining

        eta = eta + remaining_time
        print(alignment_str.format(
            task.id,
            task.name + (" (running)" if task.running else ''),
            str(remaining_time).split(".")[0],
            str(timezone.localtime(eta).strftime("%H:%M")))
        )

    remaining_duration = eta.replace(microsecond=0) - now.replace(microsecond=0)
    print(f"Estimated completion of {len(pending_tasks)} tasks in {remaining_duration}")


def queue_benchmarks(result):
    regex = result.benchmark_regex
    benchmarks = BenchmarkDB.get_by_regex(regex)
    vendors = result.vendor
    cluster = config.clusters[result.cluster]
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
            command = (f"LOG_EXCEPTIONS=1 python3 run_orchestration.py "
                       f"--benchmark '{benchmark.id}' "
                       f"--vendor {vendor.id} "
                       f"--cluster {cluster.id} ")

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

