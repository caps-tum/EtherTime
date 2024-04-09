import asyncio
import logging
import os
from asyncio import subprocess, Task
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import List, Union, Optional, Self

from ptp_perf import util
from ptp_perf.invoke import settings
from ptp_perf.invoke.environment import InvocationEnvironmentVariable, InvocationEnvironment


class InvocationFailedException(Exception):
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
    keep_alive: bool = False
    restart_delay: timedelta = timedelta(seconds=1)

    log_invocation: bool = True
    log_output: bool = True
    capture_output: bool = True
    dump_output_on_failure: bool = False

    _process: Optional[subprocess.Process] = None
    _monitor_task: Optional[Task] = None
    _logger: Optional[logging.Logger] = None
    _should_restart_process: Optional[bool] = False

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
                self.environment[name] = f"{self.environment[name]}:{value}"
            else:
                raise RuntimeError(f"Attempted to set environment variable {name} multiple times on invocation")
        else:
            self.environment[name] = value
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
        self._logger = logging.getLogger(self.command_short_name)

        actual_command = self.command.copy()

        if self.privileged:
            if os.getuid() == 0:
                # We are already root, no action necessary
                pass
            elif settings.PRIVILEGED_USING_SUDO:
                actual_command.insert(0, "sudo")
            else:
                raise InvocationFailedException("Invocation requested privileges but no privilege escalation configured.")

        if self.log_invocation:
            self._logger.info(f'{Path(self.working_directory).name} > {self.get_shell_invocation()}')

        common_invocation_arguments={
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
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

    async def read_output_lines(self, stream: asyncio.StreamReader):
        """Iterate through the process output, logging and capturing output as necessary."""
        while True:
            line = (await stream.readline()).decode()
            if line == '':
                await self._process.wait()
                break
            if line:
                if self.log_output:
                    # We don't want the extra newline if it exists
                    if line[-1] == '\n':
                        self._logger.info(f'| {line[:-1]}')
                    else:
                        self._logger.info(f'| {line}')

                if self.capture_output:
                    self.output += line

    async def _communicate(self):
        async with asyncio.TaskGroup() as read_tasks:
            read_tasks.create_task(self.read_output_lines(self._process.stdout))
            read_tasks.create_task(self.read_output_lines(self._process.stderr))

    async def _terminate(self, timeout: float = None, skip_verify_return_code: bool = False):
        """Send the program a SIGTERM to politely shut it down and then finalize the process.
        Should not be invoked directly."""

        # Send a termination/kill signal if process still running
        try:
            if self._process.returncode is None:

                # Wait for process to exit while handling IO
                try:
                    if self.log_output or self.dump_output_on_failure:
                        self._logger.info(f"Terminating {self.command_short_name}...")
                    self._process.terminate()

                    await asyncio.wait_for(self._communicate(), timeout=timeout)
                    await asyncio.wait_for(self._process.wait(), timeout=1)
                except TimeoutError:
                    pass
                finally:
                    # If process still has not exited, kill
                    if self._process.returncode is None:
                        self._logger.info(f"Killing {self.command_short_name} (shutdown timeout {timeout}s exceeded)")
                        self._process.kill()

                # Waits until exit code is available
                try:
                    await asyncio.wait_for(self._communicate(), timeout=timeout)
                    await asyncio.wait_for(self._process.wait(), timeout=1)
                except TimeoutError:
                    self._logger.warning(f"Process exit code still not valid {timeout}s after process kill.")
                    pass

        finally:
            # Verify the exit code, raise error if necessary
            self.return_code = self._process.returncode

            if self.log_invocation:
                self._logger.info(f"Process {self.command_short_name} exited with return code {self.return_code}.")

            if self.verify_return_code and not skip_verify_return_code and self.return_code != self.expected_return_code:
                if self.dump_output_on_failure:
                    for line in self.output.splitlines():
                        self._logger.info(f"| {line}")

                if self.log_output or self.dump_output_on_failure:
                    self._logger.error(f"The process {self} returned with unexpected return code {self.return_code}")

                raise InvocationFailedException(
                    f"The process {self} returned with unexpected return code {self.return_code}"
                )

    async def restart(self, kill: bool = False, ignore_return_code: bool = False, restart_delay: timedelta = timedelta(seconds=1)):
        if not kill or not ignore_return_code:
            raise NotImplementedError("Unsupported options for process restart.")

        # Signal the monitor task that we wish to restart the process
        self._should_restart_process = True
        self.restart_delay = restart_delay

        if self._process is not None:
            if self._process.returncode is None:
                try:
                    self._logger.info(f"Killing {self.command_short_name}")
                    self._process.kill()
                except ProcessLookupError:
                    pass # The process has already exited.
            else:
                raise RuntimeError("Tried to restart invocation that has already exited.")
        else:
            raise RuntimeError("Tried to restart invocation that has not been started.")


    async def _run(self) -> Self:
        """Internal API to actually run the task."""
        self._should_restart_process = True

        while self._should_restart_process:
            await self._start()
            try:
                await self._communicate()
            finally:
                # Check if keep alive value has changed
                self._should_restart_process = self.keep_alive

                # Don't check exit code if we are restarting the process.
                await self._terminate(timeout=5, skip_verify_return_code=self._should_restart_process)

            # Delay process restart to avoid too rapid looping
            if self._should_restart_process:
                await asyncio.sleep(self.restart_delay.total_seconds())
        return self


    async def run(self, timeout: float = None) -> Self:
        self.run_as_task()
        # Task is automatically cancelled if timeout or interrupted
        await asyncio.wait_for(self._monitor_task, timeout)
        return self

    @property
    def running(self) -> bool:
        return not self._monitor_task.done()

    def run_as_task(self) -> Task:
        self._monitor_task = asyncio.create_task(self._run(), name=f"Run invocation {self.command_short_name}")
        return self._monitor_task

    @property
    def command_short_name(self):
        if self.shell:
            return self.command[0].split(' ')[0]
        else:
            return self.command[0]

    async def wait(self, terminate_after = None):
        try:
            await asyncio.wait_for(self._monitor_task, timeout=terminate_after)
        except TimeoutError:
            pass
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
        return self.hide(dump_on_failure=True)

    def hide(self, dump_on_failure: bool = False) -> Self:
        self.log_invocation = False
        self.log_output = False
        self.dump_output_on_failure = dump_on_failure
        return self