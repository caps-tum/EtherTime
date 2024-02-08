import datetime
from dataclasses import field, dataclass
from datetime import timedelta
from typing import List, Optional


@dataclass
class Benchmark:

    id: str
    name : str
    tags: List[str] = field(default_factory=list)
    version: int = 1
    duration: datetime.timedelta = None

    artificial_load_network: Optional[int] = 0
    artificial_load_network_dscp_priority: Optional[str] = None
    artificial_load_cpu: Optional[int] = 0

    fault_tolerance_software_fault_interval: Optional[timedelta] = None
    fault_tolerance_software_fault_machine: Optional[str] = None

    fault_tolerance_prompt_interval: Optional[timedelta] = None
    fault_tolerance_prompt_downtime: Optional[timedelta] = None
