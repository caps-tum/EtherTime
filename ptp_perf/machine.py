import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Optional, List, Union

from ptp_perf.invoke.invocation import Invocation
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.rpc.rpc_target import RPCTarget
from ptp_perf.util import async_gather_with_progress, unpack_one_value, unpack_one_value_or_error


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
class PluginSettings:
    iperf_server: bool = False
    iperf_address: str = None
    iperf_secondary_address: str = None
    stress_ng_cpus: int = 0
    stress_ng_cpu_restrict_cores: str = None

@dataclass(kw_only=True)
class Machine(RPCTarget):
    id: str
    ptp_interface: str
    ptp_address: str
    endpoint_type: EndpointType
    ptp_force_master: bool = False
    ptp_failover_master: bool = False
    ptp_force_slave: bool = False
    ptp_software_timestamping: bool = False
    ptp_use_phc2sys: bool = True
    ptp_priority_1: int = 128
    """Clock BMCA priority, lower is better. https://blog.meinbergglobal.com/2013/11/14/makes-master-best/"""

    initial_clock_offset: Optional[timedelta] = None

    plugin_settings: Optional[PluginSettings] = None

    _ssh_session: Optional[Invocation] = None

    def ptp_force_slave_effective(self, failover_active: bool = False):
        if not failover_active:
            return self.ptp_force_slave

        # Check whether master or failover master
        # This is not really a nice way of handling it
        return not self.ptp_force_master and not self.ptp_failover_master

    @property
    def ptp_timestamp_type(self):
        return "software" if self.ptp_software_timestamping else "hardware"

    def __str__(self):
        return self.id


@dataclass
class Cluster:
    id: str
    name: str
    machines: List[Machine]

    async def synchronize_repositories(self):
        await async_gather_with_progress(
            *[machine.synchronize_repository() for machine in self.machines],
            label="Synchronizing repositories",
        )

    def machine_by_id(self, id: str):
        return unpack_one_value(machine for machine in self.machines if machine.id == id)

    def machine_by_type(self, endpoint_type: EndpointType):
        from ptp_perf.config import MACHINE_SWITCH
        # Switch is not a real machine and isn't part of the cluster.
        if endpoint_type == EndpointType.SWITCH:
            return MACHINE_SWITCH

        return unpack_one_value_or_error(
            (machine for machine in self.machines if machine.endpoint_type == endpoint_type),
            f"Could not find correct number of machines of type {endpoint_type} in cluster {self}."
        )

    @property
    def ptp_master(self) -> Machine:
        return unpack_one_value([machine for machine in self.machines if machine.ptp_force_master])

    @property
    def ptp_failover_master(self) -> Machine:
        return unpack_one_value([machine for machine in self.machines if machine.ptp_failover_master])

    def __str__(self):
        return self.name
