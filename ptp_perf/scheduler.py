import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, Tuple, List

from django.utils import timezone

from ptp_perf import config
from ptp_perf.constants import LOCAL_DIR, ensure_directory_exists
from ptp_perf.models.profile_query import ProfileQuery
from ptp_perf.models.schedule_task import ScheduleTask
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.util import user_prompt_confirmation, str_join
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
        return ScheduleTask.objects.filter(
            completion_time__isnull=True, paused=False
        ).order_by(
            '-priority', 'id',
        )

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
    alignment_str = "{0: >4} {1: >4}  {2: <80}  {3: >20}  {4: >20}"

    now = timezone.now().replace(microsecond=0)
    eta = now
    print(alignment_str.format("Id", "Prio", "Name", "Est. Time Remaining", "ETA"))
    pending_tasks = ScheduleQueue.pending_tasks()
    for task in pending_tasks:
        remaining_time = task.estimated_time_remaining

        eta = eta + remaining_time
        print(alignment_str.format(
            task.id,
            task.priority,
            task.name + (" (running)" if task.running else '') + (" (paused)" if task.paused else ''),
            str(remaining_time).split(".")[0],
            str(timezone.localtime(eta).strftime("%H:%M")))
        )

    remaining_duration = eta.replace(microsecond=0) - now.replace(microsecond=0)
    print(f"Estimated completion of {len(pending_tasks)} tasks in {remaining_duration}")


def queue_benchmarks(result):
    regex = result.benchmark_regex
    benchmarks = BenchmarkDB.get_by_regex(regex)
    vendors = result.vendor
    clusters = [config.clusters[cluster_id] for cluster_id in result.cluster] or config.ANALYZED_CLUSTERS
    priority = result.priority
    if result.duration is not None:
        duration_override = timedelta(minutes=result.duration)
    else:
        duration_override = None
    test_mode = result.test
    analyze = result.analyze
    target_count = result.target_count

    if len(vendors) == 0:
        vendors = VendorDB.ANALYZED_VENDORS
    else:
        vendors = [VendorDB.get(vendor_id) for vendor_id in vendors]

    tasks_with_index: List[Tuple[int, ScheduleTask]] = []
    for benchmark in benchmarks:
        for cluster in clusters:
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

                if target_count is not None:
                    number_tasks_to_queue = max(
                        target_count - len(ProfileQuery(benchmark=benchmark, vendor=vendor, cluster=cluster).run()), 0
                    )
                else:
                    number_tasks_to_queue = 1

                for i in range(number_tasks_to_queue):
                    tasks_with_index.append(
                        (
                            i,
                            ScheduleTask(
                                name=f"{benchmark.name} ({vendor.name}, {cluster.name})",
                                command=command,
                                estimated_time=duration,
                                priority=priority,
                            )
                        )
                    )

    # Sort by task iteration index so that tasks run interleaved.
    tasks_with_index.sort(key=lambda pair_index_task: pair_index_task[0])
    tasks = [task for index, task in tasks_with_index]

    if result.add_pause and len(tasks) > 0:
        tasks.append(
            ScheduleTask(
                name="Manual Pause",
                command=r"/bin/bash -c 'read -p \'Press any key to continue...\' -n 1 -r",
                estimated_time=timedelta(seconds=0),
                priority=priority
            )
        )

    print(str_join(tasks, "\n"))

    if len(tasks_with_index) >= 5:
        print(f'Expected runtime: {sum((task.estimated_time for task in tasks), start=timedelta(seconds=0))}')
        user_prompt_confirmation(f'Do you want to schedule these {len(tasks)} tasks?')

    ScheduleTask.objects.bulk_create(tasks)
