import datetime
from dataclasses import field, dataclass
from typing import List

from adapters.benchmark_adapter import BenchmarkAdapter


@dataclass
class Benchmark:
    id: str
    name : str
    tags: List[str] = field(default_factory=list)
    version: int = 1
    duration: datetime.timedelta = None

    adapters: List[BenchmarkAdapter] = field(default_factory=list)
