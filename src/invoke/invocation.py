import asyncio
import logging
import os
from asyncio import subprocess, Task
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union, Optional, Self

import util
from invoke import settings
from invoke.environment import InvocationEnvironmentVariable, InvocationEnvironment
from util import ImmediateException


class InvocationFailedException(ImmediateException):
    pass

@dataclass
class Invocation:
    command: List[str]

    shell: bool = False
    environment: InvocationEnvironment = field(default_factory=InvocationEnvironment)
    working_directory: Path = os.getcwd()
    privileged: bool = False

    verify_return_code: bool = True
    expected_return_code: int = 0

    log_invocation: bool = True
    log_output: bool = True
    capture_output: bool = True
    dump_output_on_failure: bool = False

    _process: Optional[subprocess.Process] = None
    _monitor_task: Optional[Task] = None

    return_code: Optional[int] = None
    output: Optional[str] = None

    @staticmethod
    def of_shell(command: str, **kwargs) -> "Invocation":
        return Invocation(
            command=[command],
            shell=True,
            **kwargs,
        )

    @staticmethod
    def of_command(*command, **kwargs) -> "Invocation":
        return Invocation(
            command=list(command),
            shell=False,
            **kwargs,
        )


    def get_shell_invocation(self):
        return util.shlex_join_polyfill(self.command)

    def as_privileged(self):
        self.privileged = True
        return self

    def set_environment_variable(self, name: str, value: str, replace: bool = False, extend: bool = False):
        if name in self.environment and not replace:
            if extend:
                self.environment[name].extend(value)
            else:
                raise RuntimeError(f"Attempted to set environment variable {name} multiple times on invocation")
        self.environment[name] = InvocationEnvironmentVariable(name, value)
        if extend:
            self.environment[name].value_as_extension()
        return self

    def set_working_directory(self, working_directory: Union[Path, str, None]) -> Self:
        self.working_directory = Path(working_directory)
        return self

    def append_arg_if_present(self, arg: Optional[str], condition: bool = True):
        if arg is not None and condition:
            self.command.append(arg)
        return self

    def set_verify_exit_code(self, verify: bool):
        self.verify_return_code = verify
        return self

    def __str__(self):
        return self.get_shell_invocation()


    async def _start(self) -> Self:
        """Actually launches the process. This should not be invoked directly."""
        # The actually launched command can differ (e.g. sudo)
        actual_command = self.command.copy()

        if self.privileged:
            if settings.PRIVILEGED_USING_SUDO:
                actual_command.insert(0, "sudo")
            else:
                raise InvocationFailedException("Invocation requested privileges but no privilege escalation configured.")

        if self.log_invocation:
            logging.info(f'{Path(self.working_directory).name} > {self.get_shell_invocation()}')

        common_invocation_arguments={
            'stdout': subprocess.PIPE,
            'stderr': subprocess.STDOUT,
            'stdin': subprocess.PIPE,
            'cwd': self.working_directory,
            'env': self.environment,
        }

        if self.shell:
            self._process = await subprocess.create_subprocess_shell(
                util.unpack_one_value_or_error(actual_command, "Attempted to invoke shell with multiple commands"),
                **common_invocation_arguments
            )
        else:
            self._process = await subprocess.create_subprocess_exec(
                *actual_command,
                **common_invocation_arguments
            )

        # Don't reset output if its already there (process restart)
        if self.capture_output and self.output is None:
            self.output = ""

        return self

    async def read_output_lines(self):
        """Iterate through the process output, logging and capturing output as necessary."""
        while True:
            line = (await self._process.stdout.readline()).decode()
            if line == '':
                await self._process.wait()
                break
            if line:
                if self.log_output:
                    # We don't want the extra newline if it exists
                    if line[-1] == '\n':
                        logging.info(f'| {line[:-1]}')
                    else:
                        logging.info(f'| {line}')

                if self.capture_output:
                    self.output += line
                yield line

    async def _communicate(self):
        async for _ in self.read_output_lines():
            pass

    async def _terminate(self, timeout: float = None, skip_verify_return_code: bool = False):
        """Send the program a SIGTERM to politely shut it down and then finalize the process.
        Should not be invoked directly."""

        # Send a termination/kill signal if process still running
        try:
            if self._process.returncode is None:

                # Wait for process to exit while handling IO
                try:
                    logging.info(f"Terminating {self.command[0]}...")
                    self._process.terminate()

                    await asyncio.wait_for(self._process.wait(), timeout=timeout)
                except TimeoutError:
                    pass
                finally:
                    # If process still has not exited, kill
                    if self._process.returncode is None:
                        logging.info(f"Killing {self.command[0]} (shutdown timeout {timeout}s exceeded)")
                        self._process.kill()

                # Waits until exit code is available
                await self._monitor_task
                await self._process.wait()

        finally:
            # Verify the exit code, raise error if necessary
            self.return_code = self._process.returncode

            if self.verify_return_code and not skip_verify_return_code and self.return_code != self.expected_return_code:
                if self.dump_output_on_failure:
                    for line in self.output.splitlines():
                        logging.info(f"| {line}")

                raise InvocationFailedException(
                    f"The process {self} returned with unexpected return code {self.return_code}"
                )

    async def restart(self, kill: bool = False, ignore_return_code: bool = False):
        if not kill or not ignore_return_code:
            raise NotImplementedError("Unsupported options for process restart.")

        if self._process is not None:
            if self._process.returncode is not None:
                try:
                    logging.info(f"Killing {self.command[0]}")
                    self._process.kill()
                except ProcessLookupError:
                    pass # The process has already exited.

            # We don't want to verify exit code.
            # await self._finalize_async(skip_verify_return_code=ignore_return_code)

        await self._start()


    async def run(self) -> Self:
        """User facing API to actually run the task."""
        await self._start()
        try:
            await self._communicate()
        finally:
            await self._terminate(timeout=5)
        return self
    
    def run_as_task(self) -> Self:
        self._monitor_task = asyncio.create_task(self.run(), name=f"Run invocation {self.command[0]}")
        return self

    async def wait(self):
        try:
            await self._monitor_task
        finally:
            self._monitor_task.cancel()
            await self._monitor_task

    async def stop(self):
        """This will finalize the process."""
        self._monitor_task.cancel()
        await self.wait()


    def run_sync(self) -> Self:
        self.run_as_task()
        return asyncio.wait_for(self.wait(), timeout=None)

    def hide_unless_failure(self) -> Self:
        self.log_invocation = False
        self.log_output = False
        self.dump_output_on_failure = True
        return self
