import asyncio
from datetime import timedelta
from unittest import IsolatedAsyncioTestCase

from utilities.multi_task_controller import MultiTaskController


class TestMultiTaskController(IsolatedAsyncioTestCase):

    async def task_regular(self, delay):
        await asyncio.sleep(delay=delay)

    async def test_cancellation(self):
        controller = MultiTaskController()
        controller.add_coroutine(self.task_regular(delay=1))

        await controller.run_for(timedelta(seconds=0.1))
        await controller.cancel_pending_tasks()

    async def test_cancel_after_completion(self):
        controller = MultiTaskController()
        controller.add_coroutine(self.task_regular(delay=0))
        await controller.run_for(timedelta(seconds=1))
        await controller.cancel_pending_tasks()
