from datetime import timedelta
from enum import Enum
from typing import List

from ptp_perf import config
from ptp_perf.profiles.base_profile import ProfileTags
from ptp_perf.profiles.benchmark import Benchmark, PTPConfig
from ptp_perf.registry.base_registry import BaseRegistry


class ResourceContentionType(str, Enum):
    UNPRIORITIZED = "unprioritized"
    PRIORITIZED = "prioritized"
    ISOLATED = "isolated"

class ResourceContentionComponent(str, Enum):
    CPU = "cpu"
    NET = "net"



class BenchmarkDB(BaseRegistry[Benchmark]):

    BASE = Benchmark("base", "Baseline", tags=[])
    TEST = Benchmark("test/test", "Test", tags=[], duration=timedelta(minutes=1))

    DEMO = Benchmark("test/demo", "Demo", tags=[], duration=timedelta(minutes=5))

    NO_SWITCH = Benchmark("configuration/no_switch", "No Switch", tags=[])
    BASE_TWO_CLIENTS = Benchmark(
        "scalability/1_to_2", "1 Master 2 Clients", tags=[],
        num_machines=3,
    )

    # Software crash, once every 30 seconds
    # ALERT: RPI7 does not have a time shift so that the logs will not jump backward in time for this benchmark!
    SOFTWARE_FAULT_SLAVE = Benchmark(
        "fault/software_fault_slave", "Software Fault (Slave)",
        tags=[ProfileTags.CATEGORY_FAULT, ProfileTags.FAULT_SOFTWARE, ProfileTags.FAULT_LOCATION_SLAVE],
        num_machines=3,
        ptp_keepalive=True,
        fault_software=True,
        fault_interval=timedelta(minutes=2),
        fault_duration=timedelta(seconds=5),
        fault_machine=config.MACHINE_RPI07.id,
    )

    HARDWARE_FAULT_SWITCH = Benchmark(
        "fault/hardware_fault_switch", "Hardware Fault (Switch)",
        tags=[ProfileTags.CATEGORY_FAULT, ProfileTags.FAULT_HARDWARE, ProfileTags.FAULT_LOCATION_SWITCH],
        num_machines=3,
        fault_hardware=True,
        fault_interval=timedelta(minutes=2),
        fault_duration=timedelta(seconds=5),
        fault_machine='switch',
    )

    HARDWARE_FAULT_SLAVE = Benchmark(
        "fault/hardware_fault_slave", "Hardware Fault (Slave)",
        tags=[ProfileTags.CATEGORY_FAULT, ProfileTags.FAULT_HARDWARE, ProfileTags.FAULT_LOCATION_SLAVE],
        num_machines=3,
        fault_hardware=True,
        fault_interval=timedelta(minutes=2),
        fault_duration=timedelta(seconds=5),
        fault_machine='rpi07',
        fault_ssh_keepalive=True,
        analyze_limit_permissible_clock_steps=None,
    )

    HARDWARE_FAULT_MASTER = Benchmark(
        "fault/hardware_fault_master", "Hardware Fault (Master)",
        tags=[ProfileTags.CATEGORY_FAULT, ProfileTags.FAULT_HARDWARE, ProfileTags.FAULT_LOCATION_MASTER],
        num_machines=3,
        fault_hardware=True,
        fault_interval=timedelta(minutes=2),
        fault_machine='rpi06',
        fault_ssh_keepalive=True,
        analyze_limit_permissible_clock_steps=None,
    )

    HARDWARE_FAULT_MASTER_FAILOVER = Benchmark(
        "fault/hardware_fault_master", "Hardware Fault (Master)",
        tags=[ProfileTags.CATEGORY_FAULT, ProfileTags.FAULT_HARDWARE, ProfileTags.FAULT_LOCATION_MASTER],
        num_machines=3,
        fault_hardware=True,
        fault_interval=timedelta(minutes=2),
        fault_machine='rpi06',
        fault_ssh_keepalive=True,
        analyze_limit_permissible_clock_steps=None,
    )


    @staticmethod
    def resource_contention(component: ResourceContentionComponent, type: ResourceContentionType, load_level: int):
        """Create a network contention benchmark for a target bandwidth.
        :param component: Which component is being artificially loaded.
        :param type: How the load should be generated.
        :param load_level: Percentage of load of (assumed GBit) interface to apply."""

        benchmark_options = {
            'id': f"load/{component.value}_{type.value}/load_{load_level}",
        }
        tags = [ProfileTags.CATEGORY_LOAD]

        # Set up component specific values
        if component == ResourceContentionComponent.NET:
            component_name = "Network"
            tags.append(ProfileTags.COMPONENT_NET)
            benchmark_options.update(
                artificial_load_network=load_level * 1000 // 100, # 1000 Mbit/s = 1 Gbit/s, load_level is percentage
            )
        elif component == ResourceContentionComponent.CPU:
            component_name = "CPU"
            tags.append(ProfileTags.COMPONENT_CPU)
            benchmark_options.update(
                artificial_load_cpu=load_level
            )
        else:
            raise RuntimeError(f"Unknown resource contention component: {component}")

        # Setup isolation specific values.
        if type == ResourceContentionType.UNPRIORITIZED:
            contention_name = "Unprioritized"
            tags.append(ProfileTags.ISOLATION_UNPRIORITIZED)

        elif type == ResourceContentionType.PRIORITIZED:
            contention_name = "Prioritized"
            tags.append(ProfileTags.ISOLATION_PRIORITIZED)

            if component == ResourceContentionComponent.NET:
                benchmark_options.update(
                    artificial_load_network_dscp_priority='cs1',
                    # CS1 is low priority traffic: https://en.wikipedia.org/wiki/Differentiated_services#Class_Selector
                )
            elif component == ResourceContentionComponent.CPU:
                benchmark_options.update(
                    artificial_load_cpu_scheduler="idle",
                    # Cannot set nice priority, so use scheduler idle instead.
                    # Nice priority +19 is lowest: https://www.man7.org/linux/man-pages/man7/sched.7.html
                )

        elif type == ResourceContentionType.ISOLATED:
            contention_name = "Isolated"
            tags.append(ProfileTags.ISOLATION_ISOLATED)

            if component == ResourceContentionComponent.NET:
                benchmark_options.update(
                    artificial_load_network_secondary_interface=True,
                )
            elif component == ResourceContentionComponent.CPU:
                benchmark_options.update(
                    artificial_load_cpu_restrict_cores=True,
                )

        else:
            raise RuntimeError(f"Unknown network contention type: {type}")

        return Benchmark(
            name=f"{contention_name} {component_name} {load_level}% Load",
            tags=tags,
            **benchmark_options,
        )


    @staticmethod
    def config_test(configuration: PTPConfig, label: str, extra_tags: List[str]):
        return Benchmark(
            f"config_test_{label}",
            f"Config Test ({label})",
            tags=[ProfileTags.CATEGORY_CONFIGURATION, *extra_tags],
            duration=timedelta(hours=1),
            ptp_config=configuration,
        )


BenchmarkDB.register_all(
    BenchmarkDB.BASE, BenchmarkDB.TEST, BenchmarkDB.DEMO,
    BenchmarkDB.BASE_TWO_CLIENTS, BenchmarkDB.SOFTWARE_FAULT_SLAVE,
    BenchmarkDB.HARDWARE_FAULT_SWITCH, BenchmarkDB.HARDWARE_FAULT_SLAVE, BenchmarkDB.HARDWARE_FAULT_MASTER,
    BenchmarkDB.NO_SWITCH,
)

for component in [ResourceContentionComponent.NET, ResourceContentionComponent.CPU]:
    for load_level in [1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        BenchmarkDB.register(BenchmarkDB.resource_contention(component, ResourceContentionType.UNPRIORITIZED, load_level=load_level))
        BenchmarkDB.register(BenchmarkDB.resource_contention(component, ResourceContentionType.UNPRIORITIZED, load_level=load_level))

    # Just one prioritized and isolated benchmark for now at 100%
    BenchmarkDB.register_all(BenchmarkDB.resource_contention(component, ResourceContentionType.PRIORITIZED, load_level=100))
    BenchmarkDB.register_all(BenchmarkDB.resource_contention(component, ResourceContentionType.ISOLATED, load_level=100))


# Different configurations
for interval in [3, 2, 1, 0, -1, -2, -3, -4, -5, -6, -7]:
    BenchmarkDB.register_all(
        BenchmarkDB.config_test(
            PTPConfig(
                log_sync_interval=interval,
                log_delayreq_interval=interval,
            ),
            label=f"interval_{interval}",
            extra_tags=[ProfileTags.CONFIGURATION_INTERVAL],
        )
    )
