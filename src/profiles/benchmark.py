import datetime
from dataclasses import field, dataclass
from datetime import timedelta
from typing import List, Optional, Literal

from constants import DEFAULT_BENCHMARK_DURATION


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

    artificial_load_network: Optional[int] = 0
    artificial_load_network_dscp_priority: Optional[str] = None
    artificial_load_network_secondary_interface: Optional[bool] = False
    artificial_load_cpu: Optional[int] = 0
    artificial_load_cpu_scheduler: Optional[str] = None
    artificial_load_cpu_restrict_cores: Optional[bool] = False

    fault_tolerance_software_fault_interval: Optional[timedelta] = None
    fault_tolerance_software_fault_machine: Optional[str] = None
    fault_tolerance_hardware_fault_interval: Optional[timedelta] = None
    fault_tolerance_hardware_fault_machine: Optional[str] = None

    fault_tolerance_prompt_interval: Optional[timedelta] = None
    fault_tolerance_prompt_downtime: Optional[timedelta] = None
