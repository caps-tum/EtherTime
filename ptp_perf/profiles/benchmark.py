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
    delay_mechanism: Literal["E2E", "P2P"] = "E2E"
    log_announce_interval: int = 1
    log_sync_interval: int = 0
    log_delayreq_interval: int = 0

    @property
    def log_log_interval(self):
        return min(self.log_announce_interval, self.log_sync_interval, self.log_delayreq_interval)

    @property
    def has_non_standard_intervals(self):
        return self.log_announce_interval != 1 or self.log_sync_interval != 0 or self.log_delayreq_interval != 0

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

    setup_use_initial_clock_offset: bool = True

    artificial_load_network: Optional[int] = 0
    artificial_load_network_dscp_priority: Optional[str] = None
    artificial_load_network_secondary_interface: Optional[bool] = False
    artificial_load_cpu: Optional[int] = 0
    artificial_load_cpu_scheduler: Optional[str] = None
    artificial_load_cpu_restrict_cores: Optional[bool] = False
    artificial_load_aux: bool = False
    artificial_load_aux_options: Optional[List[str]] = None

    fault_ssh_keepalive: bool = False
    fault_software: bool = False
    fault_hardware: bool = False
    fault_interval: Optional[timedelta] = None
    fault_duration: Optional[timedelta] = None
    fault_location: Optional[EndpointType] = None
    fault_failover: Optional[bool] = False

    monitor_resource_consumption: bool = False

    @property
    def storage_base_path(self) -> Path:
        return constants.MEASUREMENTS_DIR.joinpath(self.id)

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return self.id

    @property
    def artificial_load(self):
        if self.artificial_load_network is not None and self.artificial_load_cpu is not None:
            raise RuntimeError("Multiple artificial loads specified, invalid")
        if self.artificial_load_network is not None:
            return self.artificial_load_network
        return self.artificial_load_cpu

    @property
    def sync_interval_seconds(self) -> int:
        return 2 ** self.ptp_config.log_sync_interval
