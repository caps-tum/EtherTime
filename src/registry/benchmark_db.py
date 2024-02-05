from datetime import timedelta
from enum import Enum
from typing import Dict

from adapters.performance_degraders import NetworkPerformanceDegrader
from profiles.benchmark import Benchmark
from registry.base_registry import BaseRegistry

class NetworkContentionType(str, Enum):
    UNPRIORITIZED = "unprioritized"
    PRIORITIZED = "prioritized"
    ISOLATED = "isolated"


class BenchmarkDB(BaseRegistry):

    BASE = Benchmark("base", "Baseline", tags=[], duration=timedelta(minutes=60))
    TEST = Benchmark("test", "Test", tags=[], duration=timedelta(minutes=1))

    DEMO = Benchmark("demo", "Demo", tags=[], duration=timedelta(minutes=5))

    @staticmethod
    def network_contention(type: NetworkContentionType, load_level: int):
        """Create a network contention benchmark for a target bandwidth.
        :param type: How the load should be generated.
        :param load_level: Percentage of load of (assumed GBit) interface to apply."""
        target_bitrate = load_level * 1000 / 100 # 1000 Mbit/s = 1 Gbit/s, load_level is percentage
        if type == NetworkContentionType.UNPRIORITIZED:
            return Benchmark(
                id=f"net_{type.value}_load_{load_level}",
                name=f"Unprioritized Network {load_level}% Load",
                duration=timedelta(minutes=60),
                adapters=[
                    NetworkPerformanceDegrader(target_bandwidth=f"{target_bitrate}M"),
                ],
            )


BenchmarkDB.register_all(
    BenchmarkDB.BASE, BenchmarkDB.TEST, BenchmarkDB.DEMO,
)

for load_level in [1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
    BenchmarkDB.register(BenchmarkDB.network_contention(NetworkContentionType.UNPRIORITIZED, load_level=load_level))
