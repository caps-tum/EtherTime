import datetime
from dataclasses import field, dataclass
from datetime import timedelta
from typing import List, Optional, Literal

from ptp_perf import constants
from ptp_perf.constants import DEFAULT_BENCHMARK_DURATION


@dataclass
class PTPConfig:
    delay_mechanism: Literal["E2E", "P2P"] = "E2E"
    log_announce_interval: int = 1
    log_sync_interval: int = 0
    log_delayreq_interval: int = 0

    @property
    def log_log_interval(self):
        return min(self.log_announce_interval, self.log_sync_interval, self.log_delayreq_interval)

@dataclass
class Benchmark:

    id: str
    name : str
    tags: List[str] = field(default_factory=list)
    version: int = 1
    duration: datetime.timedelta = DEFAULT_BENCHMARK_DURATION
    num_machines: int = 2

    ptp_config: Optional[PTPConfig] = field(default_factory=PTPConfig)
    ptp_keepalive: bool = False

    analyze_limit_permissible_clock_steps: Optional[int] = 1

    artificial_load_network: Optional[int] = 0
    artificial_load_network_dscp_priority: Optional[str] = None
    artificial_load_network_secondary_interface: Optional[bool] = False
    artificial_load_cpu: Optional[int] = 0
    artificial_load_cpu_scheduler: Optional[str] = None
    artificial_load_cpu_restrict_cores: Optional[bool] = False

    fault_ssh_keepalive: bool = False
    fault_software: bool = False
    fault_hardware: bool = False
    fault_interval: Optional[timedelta] = None
    fault_duration: Optional[timedelta] = None
    fault_machine: Optional[str] = None
    fault_failover: Optional[bool] = False

    @property
    def storage_base_path(self):
        return constants.MEASUREMENTS_DIR.joinpath(self.id)

    def __str__(self):
        return f"{self.name}"
