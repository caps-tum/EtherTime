import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Union

from rpc.rpc_target import RPCTarget


@dataclass
class Process:
    program: Union[List[str], str]
    cwd: Optional[str] = None
    shell: bool = False

    check_return_code: bool = True
    expected_return_code: int = 0

    privileged: bool = False

    log_invocation: bool = True
    log_output: bool = True
    capture_output: bool = True

    _process: Optional[subprocess.Popen] = None

    return_code: Optional[int] = None
    output: Optional[str] = None

    def start(self) -> "Process":
        if self.cwd is None:
            self.cwd = os.getcwd()

        if self.log_invocation:
            logging.info(f'{Path(self.cwd).name} > {self.program}')

        self._process = subprocess.Popen(
            self.program,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            cwd=self.cwd,
            shell=self.shell,
            encoding='utf-8',
            universal_newlines=True,
        )

        if self.capture_output:
            self.output = ""

        return self

    def iterate_output(self):
        while True:
            line = self._process.stdout.readline()
            if line == '' and self._process.poll() is not None:
                break
            if line:
                if self.log_output:
                    logging.info(f'| {line.strip()}')
                self.output += line
                yield line

    def communicate(self):
        for _ in self.iterate_output():
            pass

    def stop(self):
        if self._process is not None and self._process.poll():
            self._process.kill()

    def run(self) -> str:
        """Run a configured process to completion and return the output if it succeeded, else throw an exception."""
        try:
            self.start()
            self.communicate()
        finally:
            self.stop()

        return self.output


@dataclass(kw_only=True)
class Machine(RPCTarget):
    id: str
    ptp_interface: str
    ptp_master: bool = False
    ptp_software_timestamping: bool = False
    ptp_use_phc2sys: bool = True



@dataclass
class Cluster:
    machines: List[Machine]
