import datetime
from dataclasses import field, dataclass
from datetime import timedelta
from pathlib import Path
from typing import List, Optional, Literal

from ptp_perf import constants
from ptp_perf.constants import DEFAULT_BENCHMARK_DURATION
from ptp_perf.models.endpoint_type import EndpointType


@dataclass
class PTPConfig:
    """Configuration for the PTP daemon on a machine, used to create the daemon configuration file."""
    delay_mechanism: Literal["E2E", "P2P"] = "E2E"
    """The PTP delay mechanism to use, either end to end or peer to peer."""
    log_announce_interval: int = 1
    """The interval to send announce messages from  the master, in log2 seconds (as specified by PTP)."""
    log_sync_interval: int = 0
    """The interval to send synchronization messages from the master which the slaves use to adjust their clock, in log2 seconds (as specified by PTP)."""
    log_delayreq_interval: int = 0
    """The interval that slaves send delay request messages to the master to estimate the path delay, in log2 seconds (as specified by PTP)."""

    @property
    def log_log_interval(self):
        """The minimum interval of all configured PTP intervals, used in some daemon configuration files."""
        return min(self.log_announce_interval, self.log_sync_interval, self.log_delayreq_interval)

    @property
    def has_non_standard_intervals(self):
        """Whether this PTP configuration has non-standard intervals."""
        return self.log_announce_interval != 1 or self.log_sync_interval != 0 or self.log_delayreq_interval != 0

@dataclass
class Benchmark:
    """The definition of a benchmark to run on a PTP cluster."""

    id: str
    """The unique identifier of the benchmark."""
    name : str
    """The human-readable name of the benchmark."""
    description: str = ""
    """An explanation of the benchmark and what it measures."""
    tags: List[str] = field(default_factory=list)
    """A list of tags to categorize the benchmark, any string can be chosen as a tag."""
    version: int = 1
    """The version of the benchmark definition, used to track changes to the benchmark."""
    duration: datetime.timedelta = DEFAULT_BENCHMARK_DURATION
    """The length of the benchmark, the time to run the benchmark for."""
    num_machines: int = 2
    """The number of machines to use in the benchmark, must be at least 2."""

    ptp_config: Optional[PTPConfig] = field(default_factory=PTPConfig)
    """The PTP configuration to use for the benchmark, used to create the daemon configuration file."""
    ptp_keepalive: bool = False
    """Whether to keep the PTP daemon alive by restarting it if it crashes or exits unexpectedly. Useful for benchmarks with software faults."""

    analyze_limit_permissible_clock_steps: Optional[int] = 1
    """The maximum number of clock steps that are allowed before the benchmark is considered invalid."""

    setup_use_initial_clock_offset: bool = True
    """Whether to set the initial clock offset at the beginning of the benchmark, useful for benchmarks that require a predictable starting clock offset between the master and the slaves."""

    artificial_load_network: Optional[int] = 0
    """The target bandwidth to use for artificial network load benchmark in megabits per second."""
    artificial_load_network_dscp_priority: Optional[str] = None
    """The DSCP priority to use for the iPerf traffic in the artificial network load benchmark."""
    artificial_load_network_secondary_interface: Optional[bool] = False
    """Whether to use a secondary network interface for artificial load in the artificial network load benchmark."""
    artificial_load_cpu: Optional[int] = 0
    """The target CPU load to use with Stress-NG for the artificial CPU load benchmark as a percentage."""
    artificial_load_cpu_scheduler: Optional[str] = None
    """The CPU scheduler to use for Stress-NG in the artificial CPU load benchmark."""
    artificial_load_cpu_restrict_cores: Optional[bool] = False
    """Whether to restrict the CPU cores used by Stress-NG in the artificial CPU load benchmark using task affinity."""
    artificial_load_aux: bool = False
    """Whether this is an auxiliary artificial load benchmark that uses Stress-NG, such as memory bandwidth load, cache contention, etc."""
    artificial_load_aux_options: Optional[List[str]] = None
    """Options to pass to Stress-NG for this auxiliary load benchmark."""

    fault_ssh_keepalive: bool = False
    """Whether to keep the SSH connection from the orchestrator to the workers and the worker PTP-Perf applications alive by restarting them upon unexpected disconnects or exits. Useful for benchmarks with hardware faults."""
    fault_software: bool = False
    """Whether to simulate software faults during the benchmark."""
    fault_hardware: bool = False
    """Whether to simulate hardware faults during the benchmark."""
    fault_interval: Optional[timedelta] = None
    """How frequently a fault is generated."""
    fault_duration: Optional[timedelta] = None
    """How long a fault lasts."""
    fault_location: Optional[EndpointType] = None
    """The location of the fault, e.g. the machine to create the fault on."""
    fault_failover: Optional[bool] = False
    """Whether to use a failover master during the fault in this benchmark. If activated, secondary slaves will be assigned the failover role and will be temporarily promoted to master if the primary master fails."""

    monitor_resource_consumption: bool = False
    """Capture system resource metrics during the benchmark run."""

    @property
    def storage_base_path(self) -> Path:
        return constants.MEASUREMENTS_DIR.joinpath(self.id)

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return self.id

    @property
    def artificial_load(self):
        """The target artificial load for the benchmark, either network or CPU load."""
        if self.artificial_load_network is not None and self.artificial_load_cpu is not None:
            raise RuntimeError("Multiple artificial loads specified, invalid")
        if self.artificial_load_network is not None:
            return self.artificial_load_network
        return self.artificial_load_cpu

    @property
    def sync_interval_seconds(self) -> int:
        """The actual (non-log scale) synchronization interval in seconds."""
        return 2 ** self.ptp_config.log_sync_interval

    def summary_markdown(self):
        return (
            "### Benchmark: " + self.name + "\n"
            f"_id: `{self.id}`, {self.num_machines} machines, {self.duration} duration._\n"
            + self.description
        )

    def summary_text(self):
        return (
            f"Benchmark: {self.name}\n"
            f"  id: {self.id}, {self.num_machines} machines, {self.duration} duration.\n"
            f"{self.description}"
        )
