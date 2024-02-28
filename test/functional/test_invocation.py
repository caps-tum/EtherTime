import asyncio
from datetime import datetime, timedelta
from unittest import IsolatedAsyncioTestCase

from invoke.invocation import Invocation
from util import setup_logging


class TestInvocation(IsolatedAsyncioTestCase):



    async def asyncSetUp(self):
        setup_logging()

    async def test_process_restart(self):
        invocation = Invocation.of_command("sleep", "1")
        start = datetime.now()
        task = invocation.run_as_task()
        await asyncio.sleep(0.5)
        await invocation.restart(kill=True, ignore_return_code=True)
        await task
        stop = datetime.now()
        elapsed = stop - start
        self.assertGreater(elapsed, timedelta(seconds=1.5))
        self.assertLess(elapsed, timedelta(seconds=1.7))


    async def test_process_restart_if_already_exited(self):
        invocation = Invocation.of_command("true")
        task = invocation.run_as_task()
        await task

        with self.assertRaises(RuntimeError):
            await invocation.restart(kill=True, ignore_return_code=True)
