import asyncio
import logging
from asyncio import Task
from asyncio.exceptions import CancelledError
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from datetime import timedelta
from typing import List, Coroutine


@dataclass
class MultiTaskController:
    background_tasks: List[Task] = field(default_factory=list)
    exit_stack: AsyncExitStack = field(default_factory=AsyncExitStack)

    async def run_for(self, duration: timedelta = None):
        if duration is not None:
            timeout = duration.total_seconds()
        else:
            timeout = None

        try:
            await asyncio.wait(
                self.background_tasks, timeout=timeout, return_when=asyncio.FIRST_COMPLETED,
            )
        except TimeoutError:
            pass

    async def cancel_pending_tasks(self):
        try:
            await self.exit_stack.aclose()
        except CancelledError:
            logging.warning(f"Tasks were cancelled during multitasking.")
        self.background_tasks.clear()


    @staticmethod
    async def _stop_task(task: Task):
        try:
            if not task.done():
                task.cancel()
                await task
                task.result()
        except CancelledError:
            logging.warning(f"Task '{task.get_name()}' was cancelled")

    def add_coroutine(self, coroutine: Coroutine, label: str = None):
        task = asyncio.create_task(coroutine, name=label)
        self.add_task(task)

    def add_task(self, task: Task):
        self.background_tasks.append(task)
        self.exit_stack.push_async_callback(self._stop_task, task)
