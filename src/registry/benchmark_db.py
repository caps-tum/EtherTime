from datetime import timedelta
from typing import Dict

from profiles.benchmark import Benchmark
from registry.base_registry import BaseRegistry


class BenchmarkDB(BaseRegistry):

    BASE = Benchmark("base", "Baseline", tags=[], duration=timedelta(minutes=60))
    TEST = Benchmark("test", "Test", tags=[], duration=timedelta(minutes=1))


BenchmarkDB.register_all(
    BenchmarkDB.BASE, BenchmarkDB.TEST
)
