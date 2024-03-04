import asyncio
from asyncio import CancelledError
from unittest import IsolatedAsyncioTestCase

from ptp_perf.invoke.invocation import Invocation
from ptp_perf.util import setup_logging


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


    async def test_process_keepalive(self):
        invocation = Invocation.of_shell("echo OK")
        invocation.keep_alive = True

        task = invocation.run_as_task()
        await asyncio.sleep(1.5)
        task.cancel()
        with self.assertRaises(CancelledError):
            await task
        self.assertListEqual(["OK"] * 2, invocation.output.splitlines())
