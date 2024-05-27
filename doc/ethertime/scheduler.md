# Getting Started with Using the Scheduler in `scheduler.py`

The `scheduler.py` script in the `ptp_perf` directory is a command-line tool for managing tasks in the EtherTime project. This guide will walk you through the process of using this scheduler.

## 1. Understanding the Scheduler

The scheduler is designed to process tasks in a queue. Tasks are processed in priority order, and only one task is processed at a time. The scheduler will run indefinitely until stopped.

A task is a command to run on the orchestrator. The tasks will be executed by priority and in the order they were queued. The time parameter limits the task execution time, after which the task is considered to have timed out and will therefore be terminated.

## 2. Running the Scheduler

To run the scheduler, use the `run` command:

```bash
python3 scheduler.py run
```

This will start the scheduler, which will begin processing tasks in the queue. The scheduler will run indefinitely until stopped, and queries the database for new tasks to process.

Open a new terminal window to queue tasks while the scheduler is running.

## 3. Adding a Task to the Queue

To add a single task to the queue, use the `queue` command:

```bash
python3 scheduler.py queue --name "Task Name" --command "echo Hello world" --time 10
```

Tasks can represent benchmarks, tests, or other operations that need to be performed on the orchestrator. Each task is a wrapper around a shell command. Usually, tasks will be used to execute benchmarks on the testbed, for which the `queue-benchmarks` command provides a shortcut.

Replace `"Task Name"` with a name for the task, `"echo Hello world"` with the shell command to run, and `10` with the estimated task time in minutes. A slack time of 5 minutes is added before the command is considered to have timed out.

## 4. Queueing Multiple Benchmarks

To queue multiple benchmarks, use the `queue-benchmarks` command:

```bash
python3 scheduler.py queue-benchmarks --benchmark-regex "base" --vendor ptpd --cluster testcluster --target-count 10 --priority 0
```

Replace `"base"` with a regex for filtering benchmark ids, `ptpd` with the vendor id, `testcluster` with the cluster id, `10` with the number of profiles to target, and `0` with the priority to assign to scheduled tasks.

Additional options are available, refer to the command help for more information.

## 5. Retrieving Queue Status

To retrieve the current queue status, use the `info` command:

```bash
python3 scheduler.py info
```

This will show the current queue status and the number of tasks in the queue, as well as the estimated time to completion.

## 6. Listing Available Benchmarks

To list available benchmarks and their descriptions, use the `available` command:

```bash
python3 scheduler.py available
```

This will allow you to see which benchmarks are available for testing various aspects of the time synchronization protocols.


That's it! You've successfully queued the first benchmark and it will be processed by the scheduler in due time. You can add more tasks to the queue as needed, and the scheduler will process them by priority and in the order they were queued.

For more information on the scheduler, refer to the inline comments in `scheduler.py`.
