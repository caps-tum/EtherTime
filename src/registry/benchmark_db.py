from datetime import timedelta
from enum import Enum

import config
from profiles.base_profile import ProfileTags
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

    BASE_TWO_CLIENTS = Benchmark("1_to_2", "1 Master 2 Clients", tags=[], duration=timedelta(minutes=60))

    # Software crash, once every 30 seconds
    SOFTWARE_FAULT = Benchmark(
        "software_fault", "Software Fault", tags=[ProfileTags.CATEGORY_FAULT, ProfileTags.FAULT_SOFTWARE], duration=timedelta(minutes=60),
        fault_tolerance_software_fault_interval=timedelta(seconds=30),
        fault_tolerance_software_fault_machine=config.MACHINE_RPI07.id,
    )

    HARDWARE_FAULT_SWITCH = Benchmark(
        "hardware_fault_switch", "Hardware Fault (Switch)",
        tags=[ProfileTags.CATEGORY_FAULT, ProfileTags.FAULT_HARDWARE, ProfileTags.FAULT_LOCATION_SWITCH],
        duration=timedelta(minutes=5),
        fault_tolerance_prompt_interval=timedelta(seconds=30),
        fault_tolerance_prompt_downtime=timedelta(seconds=5),
    )

    @staticmethod
    def network_contention(type: NetworkContentionType, load_level: int):
        """Create a network contention benchmark for a target bandwidth.
        :param type: How the load should be generated.
        :param load_level: Percentage of load of (assumed GBit) interface to apply."""

        common_options = {
            'artificial_load_network': load_level * 1000 // 100, # 1000 Mbit/s = 1 Gbit/s, load_level is percentage
            'duration': timedelta(minutes=60),
        }

        if type == NetworkContentionType.UNPRIORITIZED:
            return Benchmark(
                id=f"net_{type.value}_load_{load_level}",
                name=f"Unprioritized Network {load_level}% Load",
                tags=[ProfileTags.CATEGORY_LOAD, ProfileTags.COMPONENT_NET, ProfileTags.ISOLATION_UNPRIORITIZED],
                **common_options,
            )
        if type == NetworkContentionType.PRIORITIZED:
            return Benchmark(
                id=f"net_{type.value}_load_{load_level}",
                name=f"Prioritized Network {load_level}% Load",
                tags=[ProfileTags.CATEGORY_LOAD, ProfileTags.COMPONENT_NET, ProfileTags.ISOLATION_PRIORITIZED],
                artificial_load_network_dscp_priority='cs1', # CS1 is low priority traffic: https://en.wikipedia.org/wiki/Differentiated_services#Class_Selector
                **common_options,
            )
        else:
            raise RuntimeError(f"Unknown network contention type: {type}")


BenchmarkDB.register_all(
    BenchmarkDB.BASE, BenchmarkDB.TEST, BenchmarkDB.DEMO,
    BenchmarkDB.BASE_TWO_CLIENTS, BenchmarkDB.SOFTWARE_FAULT, BenchmarkDB.HARDWARE_FAULT_SWITCH,
)

for load_level in [1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
    BenchmarkDB.register(BenchmarkDB.network_contention(NetworkContentionType.UNPRIORITIZED, load_level=load_level))

# Just one prioritized benchmark for now at 100%
BenchmarkDB.register_all(BenchmarkDB.network_contention(NetworkContentionType.PRIORITIZED, load_level=100))
