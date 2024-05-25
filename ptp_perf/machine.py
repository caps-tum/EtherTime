import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from pathlib import Path
from typing import Optional, List, Union

from ptp_perf.invoke.invocation import Invocation
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.rpc.rpc_target import RPCTarget
from ptp_perf.util import async_gather_with_progress, unpack_one_value, unpack_one_value_or_error


@dataclass(kw_only=True)
class PluginSettings:
    """Settings for PTP-Perf plugins that are run on a worker during benchmarking."""
    iperf_server: bool = False
    """Whether to run an iperf server on the machine for network load contention benchmarks.
    If this is False, will run an iperf client instead."""
    iperf_address: str = None
    """The local worker's IP address to use for iperf. Must be set if iperf_server is True."""
    iperf_secondary_address: str = None
    """The alternative IP address to use for iperf on a secondary network. This is used for the isolated network benchmark. Must be set if iperf_server is True."""
    stress_ng_cpus: int = 0
    """The number of CPUs to stress with stress-ng. Must be set for the CPU load benchmarks."""
    stress_ng_cpu_restrict_cores: str = None
    """The CPU cores to restrict stress-ng to via task affinity. Must be set for the CPU load isolated benchmarks."""

class MachineClientType(StrEnum):
    """The effective role of a machine in the PTP cluster, calculated based on the endpoint type and the benchmark. This is used to determine the PTP configuration for the worker."""
    MASTER = "master"
    """The worker is the primary master of the PTP cluster for this benchmark."""
    FAILOVER_MASTER = "failover_master"
    """The worker is the failover master of the PTP cluster for this benchmark."""
    SLAVE = "SLAVE"
    """The worker is a slave in the PTP cluster for this benchmark."""

    def is_master_or_failover(self) -> bool:
        return self == MachineClientType.MASTER or self == MachineClientType.FAILOVER_MASTER

    def is_primary_master(self) -> bool:
        return self == MachineClientType.MASTER

    def is_slave(self) -> bool:
        return self == MachineClientType.SLAVE


@dataclass(kw_only=True)
class Machine(RPCTarget):
    """A machine that is part of a cluster used for benchmarking."""

    id: str
    """The unique identifier of the machine."""
    ptp_interface: str
    """The network interface that PTP should run on."""
    ptp_address: str
    """The IP address of the machine to use with PTP."""
    endpoint_type: EndpointType
    """The role of the machine in the PTP cluster."""
    ptp_software_timestamping: bool = False
    """Whether to use software timestamping for PTP. If False, hardware timestamping is used."""
    ptp_use_phc2sys: bool = True
    """Whether to use phc2sys to synchronize the system clock with the PTP clock, only relevant for LinuxPTP."""
    python_executable: str = "python3"
    """The path to the Python executable to use for running scripts on the machine. May be used for virtual environments or different python versions."""

    initial_clock_offset: Optional[timedelta] = None
    """The initial clock offset of the machine to set after a preparatory synchronization run with Chrony. 
    This allows a predictable clock offset to be set for the machine before the benchmarking run starts.
    If None, the machine will be synchronized with the master."""

    plugin_settings: Optional[PluginSettings] = None
    """Settings for PTP-Perf plugins that can be run on the machine."""

    shutdown_delay: timedelta = timedelta(minutes=0)
    """The delay passed to the shutdown command to allow the machine to shut down gracefully.
    For most boards, no delay is required, but for some, a delay is needed to ensure that the SSH connection is not dropped before the command completes.
    Only supports full minutes."""

    _ssh_session: Optional[Invocation] = None
    """The active SSH session to the machine."""

    def get_effective_client_type(self, failover_active: bool = False) -> MachineClientType:
        """Return the effective client type of the machine, taking into account the failover state of the cluster."""
        return {
            EndpointType.MASTER: MachineClientType.MASTER,
            EndpointType.PRIMARY_SLAVE: MachineClientType.SLAVE,
            EndpointType.SECONDARY_SLAVE: MachineClientType.SLAVE if not failover_active else MachineClientType.FAILOVER_MASTER,
            EndpointType.TERTIARY_SLAVE: MachineClientType.SLAVE,
        }[self.endpoint_type]

    def invoke_ssh(self, command: str, ssh_options: List[str] = None):
        if ssh_options is None:
            ssh_options = []

        return Invocation.of_command(
            "ssh", *ssh_options, self.address, command
        )

    @property
    def ptp_priority_1(self):
        """Clock BMCA priority, lower is better. https://blog.meinbergglobal.com/2013/11/14/makes-master-best/"""
        return {
            EndpointType.MASTER: 1,
            # This is potentially the failover master
            EndpointType.SECONDARY_SLAVE: 200,
            # These are always slaves
            EndpointType.PRIMARY_SLAVE: 248,
            EndpointType.TERTIARY_SLAVE: 248,
        }[self.endpoint_type]

    @property
    def ptp_timestamp_type(self):
        return "software" if self.ptp_software_timestamping else "hardware"

    def __str__(self):
        return self.id


@dataclass
class Cluster:
    """A cluster of machines that can be used for benchmarking."""
    id: str
    """The unique identifier of the cluster."""
    name: str
    """The human-readable name of the cluster."""
    machines: List[Machine]
    """A list of machines that are part of the cluster."""

    async def synchronize_repositories(self):
        """Synchronize the local PTP-Perf repository to all machines in the cluster via rsync."""
        await async_gather_with_progress(
            *[machine.synchronize_repository() for machine in self.machines],
            label="Synchronizing repositories",
        )

    def subset_cluster(self, num_machines):
        """Shrink the number of machines in this cluster, returning a new cluster with only the first {num_machines} machines."""
        return Cluster(
            id=self.id,
            name=self.name,
            machines=self.machines[0:num_machines],
        )

    def machine_by_id(self, id: str):
        """Find a machine in the cluster by its unique identifier."""
        return unpack_one_value(machine for machine in self.machines if machine.id == id)

    def machine_by_type(self, endpoint_type: EndpointType):
        """Find a machine in the cluster by its endpoint type. It is an error to use this if the cluster has multiple machines of the same type."""
        return unpack_one_value_or_error(
            self.machines_by_type(endpoint_type),
            f"Could not find correct number of machines of type {endpoint_type} in cluster {self}."
        )

    def machines_by_type(self, endpoint_type: EndpointType) -> List[Machine]:
        """Find all machines in the cluster by their endpoint type."""
        from ptp_perf.config import MACHINE_SWITCH, MACHINE_SWITCH2
        # Switch is not a real machine and isn't part of the cluster.
        if endpoint_type == EndpointType.SWITCH:
            return [MACHINE_SWITCH, MACHINE_SWITCH2]

        return [machine for machine in self.machines if machine.endpoint_type == endpoint_type]


    @property
    def ptp_master(self) -> Machine:
        """The master of the PTP cluster. There should only ever be one master in the cluster."""
        return unpack_one_value([machine for machine in self.machines if machine.endpoint_type == EndpointType.MASTER])

    @property
    def ptp_failover_master(self) -> Optional[Machine]:
        """The failover master of the PTP cluster. There may be zero or one failover masters in the cluster."""
        try:
            return unpack_one_value([machine for machine in self.machines if machine.endpoint_type == EndpointType.SECONDARY_SLAVE])
        except ValueError:
            return None

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id
