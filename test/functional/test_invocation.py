import asyncio
from datetime import datetime, timedelta
from unittest import IsolatedAsyncioTestCase

from invoke.invocation import Invocation
from util import setup_logging


class TestInvocation(IsolatedAsyncioTestCase):



    async def asyncSetUp(self):
        setup_logging()

    async def test_process_restart(self):
        invocation = Invocation.of_shell("sleep 1; echo OK")
        task = invocation.run_as_task()
        await asyncio.sleep(0.5)
        self.assertNotIn("OK", invocation.output)
        await invocation.restart(kill=True, ignore_return_code=True)
        await task
        self.assertIn("OK", invocation.output)


    async def test_process_restart_if_already_exited(self):
        invocation = Invocation.of_command("true")
        task = invocation.run_as_task()
        await task

        with self.assertRaises(RuntimeError):
            await invocation.restart(kill=True, ignore_return_code=True)
