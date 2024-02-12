import asyncio
import enum
import inspect
import logging
import os
import re
import shlex
import signal
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Iterable, Optional, Dict, Coroutine, Callable, Union, TypeVar


class FormatColors(enum.Enum):
    none = ""
    grey = "\x1b[38;1m"
    yellow = "\x1b[33;1m"
    red = "\x1b[31;1m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"


class ColoredFormatter(logging.Formatter):
    use_colors: bool = True
    level_colors = {
        logging.DEBUG: FormatColors.grey,
        logging.INFO: FormatColors.none,
        logging.WARNING: FormatColors.yellow,
        logging.ERROR: FormatColors.red,
        logging.CRITICAL: FormatColors.bold_red
    }

    def format(self, record):
        if self.use_colors:
            return self.level_colors[record.levelno].value + super().format(record) + FormatColors.reset.value
        return super().format(record)


def setup_logging(log_file=None, log_invocation_command=False, log_file_mode='a'):
    handlers = [
        logging.StreamHandler()
    ]
    if log_file:
        handlers.append(logging.FileHandler(log_file, mode=log_file_mode, encoding='utf-8'))

    formatter = ColoredFormatter()
    formatter.use_colors = sys.stdout.isatty()

    # Only color the stream handler
    handlers[0].setFormatter(formatter)

    # https://youtrack.jetbrains.com/issue/PY-39762
    # noinspection PyArgumentList
    logging.basicConfig(
        level=logging.INFO,
        handlers=handlers,
        force=True,
    )
    if log_invocation_command or os.getenv("DDS_PERF_LOG_INVOCATION_COMMAND"):
        if hasattr(shlex, 'join'):
            logging.info(f'> {shlex.join(sys.argv)}')
        else:
            logging.info(f'> {" ".join(sys.argv)}')


def run(program, input='', cwd=None, shell=True, exit_code=0, print_output=True, timeout=None):
    if timeout is not None:
        program = f"timeout {timeout} {program}"

    output = ''
    with SyncSafeSubprocess(program, cwd, shell, exit_code, print_output) as process:
        if input:
            process.process.stdin.write(input.encode('utf-8'))

        for line in process.iterate_output():
            output += line

    return output


def process_open(program, cwd=None, shell=True):
    if cwd is None:
        cwd = os.getcwd()

    logging.info(f'{Path(cwd).name} > {program}')

    return subprocess.Popen(
        program,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
        cwd=cwd,
        shell=shell,
        encoding='utf-8',
        universal_newlines=True,
    )


@dataclass
class SyncSafeSubprocess:
    program: str
    cwd: str = None
    shell: bool = True
    exit_code: Optional[int] = 0
    print_output: bool = True
    process: subprocess.Popen = None

    def __enter__(self):
        self.process = process_open(self.program, self.cwd, self.shell)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.process is not None and self.process.poll() is None:
            logging.warning(f"Terminating subtask: {self.program}")
            self.process.kill()
        self.process.poll()
        if self.exit_code is not None and self.process.returncode != self.exit_code:
            raise RuntimeError(f"Program {self.program} exited with unexpected output code {self.process.returncode}.")

    def iterate_output(self):
        while True:
            line = self.process.stdout.readline()
            if line == '' and self.process.poll() is not None:
                break
            if line:
                if self.print_output:
                    logging.info(f'| {line.strip()}')
                yield line

    def iterate_output_by_character(self):
        while True:
            block = self.process.stdout.read(1)
            if block == '' and self.process.poll() is not None:
                break
            if block:
                if self.print_output:
                    logging.info(f'| {block.strip()}')
                yield block


def create_latex_define(name, value):
    if re.search("[^0-9A-Za-z_]", name):
        raise RuntimeError(f"Cannot convert definition '{name}' into a latex command due to invalid characters")
    return rf"\newcommand{{\{name}}}{{{value}}}" + '\n'


def latex_escape(input: str):
    return input.replace("_", "\_")

T = TypeVar("T")

def unpack_one_value(param: Iterable[T]) -> T:
    """
    Unpack a single value from an iterable. Fail when there are zero elements or more than one element.
    :param param: Iterable to fetch one value from
    :return: The single value unpacked
    """
    [value] = param
    return value


def unpack_one_value_or_error(param: Iterable[T], message: str) -> T:
    """
    Unpack a single value from an iterable. Fail when there are zero elements or more than one element.
    :param param: Iterable to fetch one value from
    :param message: Error message on failure.
    :return: The single value unpacked
    """
    try:
        [value] = param
        return value
    except ValueError as e:
        raise RuntimeError(f"{message} ({e})")


@dataclass
class AsyncSafeSubprocess:
    cmd_options: List[str]
    shell: bool = False
    process: asyncio.subprocess.Process = None
    verify_exit_code: bool = True

    async def __aenter__(self):
        logging.info(f"> {self.cmd_options_formatted}")
        if self.shell:
            self.process = await asyncio.create_subprocess_shell(
                *self.cmd_options,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
            )
        else:
            self.process = await asyncio.create_subprocess_exec(
                *self.cmd_options,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.process.returncode is None:
            logging.info(f"Terminating {self.cmd_options_formatted}"),
            self.process.send_signal(signal.SIGINT)
            await self.process.wait()
            logging.info(f"Process exited with status: {self.process.returncode}"),
        if exc_type is None:
            if not self.check_returncode():
                raise RuntimeError(
                    f"Process {self.cmd_options_formatted} exited with unexpected status code: {self.process.returncode}")

    def check_returncode(self):
        return not self.verify_exit_code or self.process.returncode == 0

    @property
    def cmd_options_formatted(self):
        if self.shell:
            return shlex.join(self.cmd_options)
        else:
            return ' '.join(f"{option}" for option in self.cmd_options)

    async def iterate_output_by_character(self):
        while True:
            block = await self.process.stdout.read(1)
            if len(block) == 0:
                await self.process.wait()
                break
            block = block.decode()
            if block:
                # print(block)
                # sys.stdout.flush()
                yield block

    async def iterate_output(self):
        async for line in async_subprocess_iter_output(self):
            yield line

    async def collect_output(self) -> str:
        output = ""
        async for line in self.iterate_output():
            output += line + "\n"
        return output

    async def dump_output_on_failure(self):
        output = await self.collect_output()
        if not self.check_returncode():
            for line in output.splitlines():
                logging.info(f"| {line}")

    async def yield_progress_and_dump_on_failure(self):
        all_output = ""
        num_lines = 0
        async for line in self.iterate_output():
            all_output += line + "\n"
            num_lines += 1
            yield num_lines
        if not self.check_returncode():
            for line in all_output.splitlines():
                logging.info(f"| {line}")

    async def start(self):
        return await self.__aenter__()


async def async_subprocess_iter_output(process):
    while True:
        data = await process.process.stdout.readline()
        if not data:
            await process.process.wait()
            break
        yield data.decode()


async def async_run_subprocess(*cmd_options, shell=False):
    async with AsyncSafeSubprocess(*cmd_options, shell=shell) as process:
        yield async_subprocess_iter_output(process)


@dataclass
class SafeGatherError(Exception):
    origins: List[BaseException]

    def __str__(self):
        return f"Task execution resulted in the following errors: " \
               + "".join(f"{origin}" for origin in self.origins)

    def traceback(self):
        for origin in self.origins:
            logging.exception(origin)

    def log(self):
        logging.error("Task execution resulted in the following errors:")
        for origin in self.origins:
            log_exception(origin)


async def async_safe_gather(*tasks):
    results = await asyncio.gather(
        *tasks,
        return_exceptions=True
    )
    exceptions = []
    for result in results:
        if isinstance(result, BaseException):
            exceptions.append(result)
    if len(exceptions) > 0:
        raise SafeGatherError(exceptions)
    return results


async def async_process_communicate(process: AsyncSafeSubprocess, label: str = None):
    prefix = f"[{label}] | " if label else ""
    async for line in async_subprocess_iter_output(process):
        logging.info(f"{prefix}{line.strip()}")


def async_to_sync(coroutine: Coroutine):
    return asyncio.run(coroutine)

def log_exception(exc_val, force_traceback: bool = False):
    if isinstance(exc_val, Exception):
        logging.error(f"Error: {exc_val}")
        if os.getenv("LOG_EXCEPTIONS") == "1" or force_traceback:
            traceback.print_exception(exc_val)
    elif isinstance(exc_val, BaseException):
        logging.warning(f"Exiting due to request.")

class ImmediateException(Exception):
    """Exception that is logged as an error immediately upon construction."""

    def __init__(self, *args):
        super().__init__(*args)
        logging.error(self)


@dataclass
class StackTraceGuard:
    exit_code: int = 255

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        log_exception(exc_val)
        if exc_val is not None and self.exit_code:
            exit(self.exit_code)
        return True


def flat_map(function, collection: Iterable):
    results = []
    for item in collection:
        results += function(item)
    return results


def num_usable_processors():
    """Get the number of threads available to this process and its children, which is different from the number of
    available CPUs. """
    return len(os.sched_getaffinity(0))


def str_join(items: Iterable, separator: str = ", ", format: str = "{}"):
    """Collapse the iterable of items into their string representations and join them using the separator."""
    return separator.join(format.format(item) for item in items)

def unique_str_join(items: Iterable, **kwargs):
    """Collapse items into their string representations and join them, but ignore any duplicates."""
    return str_join(set(items), **kwargs)

def shlex_join_polyfill(split_command):
    """
    Return a shell-escaped string from *split_command*.
    For backward compatibility with python 3.7
    From: https://github.com/python/cpython/blob/559d0e8073e223acad1f41f24c8a8fd6aa6abb81/Lib/shlex.py#L319
    :return:
    """
    if hasattr(shlex, "join"):
        return shlex.join(split_command)
    return ' '.join(shlex.quote(arg) for arg in split_command)


async def async_gather_with_progress(*coroutines: Coroutine[None, None, T], label: str = "Tasks running") -> List[T]:
    tasks = [asyncio.create_task(coroutine) for coroutine in coroutines]

    pending = tasks
    done = []
    while len(pending) > 0:
        logging.info(f"{label} ({len(done)}/{len(tasks)} completed)\033[A")
        done, pending = await asyncio.wait(tasks, timeout=1)

    logging.info(f"{label} ({len(done)}/{len(tasks)} completed, {len([task for task in tasks if task.exception()])} errors)")
    # First print all the errors
    for task in tasks:
        if task.exception() is not None:
            logging.error(f"{label} error: {task.exception()}")
    # Now re-raise them if there were errors, else return all results.
    return [task.result() for task in tasks]

async def async_wait_for_condition(get_progress: Callable, target: int = 1, label: str = "Tasks running"):
    while True:
        if inspect.iscoroutinefunction(get_progress):
            progress = await get_progress()
        else:
            progress = get_progress()

        if progress == target:
            break
        logging.info(f"{label} ({progress}/{target} completed)\033[A")
        await asyncio.sleep(0.5)
    logging.info(f"{label} ({progress}/{target} completed)")


def time_since_epoch_seconds():
    return int(time.time())

def user_prompt_confirmation(prompt: str):
    logging.warning(prompt)
    while True:
        response = input("Do you want to continue? [y/n]: ")
        if response.lower() == "y":
            return
        if response.lower() == "n":
            raise RuntimeError("User declined confirmation.")
        logging.info("Please type [y] or [n].")

def user_select(prompt: str, options: List[str]):
    logging.warning(prompt)
    while True:
        response = input(f"Please select option [{str_join(options, separator='/')}]: ")
        if response in options:
            return response
        logging.info(f"Input not understood.")

def unpack_single_value_if_possible(values: List):
    """If list has just a single value, unwrap it. Else, return the list.
    [3] -> 3
    [3, 2] -> [3, 2]
    """
    if values is None:
        return values
    if len(values) == 1:
        return values[0]
    return values

def pack_single_value_if_necessary(values):
    """Pack values into a list if they are not already in a list"""
    if isinstance(values, List):
        return values
    return [values]

def check_both_or_no_variables_set(var1, var2, error_message="Only one variable set but both or none required."):
    if (var1 is not None) ^ (var2 is not None):
        raise ValueError(error_message)
    return var1 is not None or var2 is not None


def safe_zip(iterable1, iterable2):
    assert len(iterable1) == len(iterable2)
    return zip(iterable1, iterable2)

def value_or_default(value, default):
    """Return value if and only if it is not none, else return default."""
    return value if value is not None else default


def determine_number_of_git_commits(path: str):
    return int(
        subprocess.check_output(
            ["git", "rev-list", "--count", "HEAD", "--", "."],
            cwd=path,
        )
    )

def add_indentation(lines: str, num_spaces: int = 4):
    return str_join(
        [str(" " * num_spaces) + line for line in lines.splitlines(keepends=True)],
        separator="",
    )


class ConditionNotMetException(Exception):
    pass

def wait_for(condition: Callable[[], bool],
             retries: int = 6, interval: float = 0.5,
             raise_on_fail: bool = True, fail_msg="The condition was not met."):
    """Wait for a condition to become true with certain number of {retries} each spaced {interval} seconds.
    By default, raises a ConditionNotMetException when the number of retries is exhausted.
    The first condition check is immediate."""
    for retry in range(retries):
        if condition():
            return True
        time.sleep(interval)

    if raise_on_fail:
        raise ConditionNotMetException(fail_msg)
    else:
        return False

PathOrStr = Union[Path, str]
