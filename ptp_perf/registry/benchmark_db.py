from datetime import timedelta
from typing import List

from ptp_perf import config
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.profiles.base_profile import ProfileTags
from ptp_perf.profiles.benchmark import Benchmark, PTPConfig
from ptp_perf.profiles.taxonomy import ResourceContentionType, ResourceContentionComponent
from ptp_perf.registry.base_registry import BaseRegistry


# Some benchmark recipies
def benchmark_scalability(num_nodes: int):
    return Benchmark(
        f"scalability/1_to_{num_nodes - 1}", f"{num_nodes} Nodes", tags=[],
        num_machines=num_nodes,
        monitor_resource_consumption=True,
    )


class BenchmarkDB(BaseRegistry[Benchmark]):

    BASE = Benchmark("base", "Baseline", tags=[])
    TEST = Benchmark("test/test", "Test", tags=[], duration=timedelta(minutes=1))

    DEMO = Benchmark("test/demo", "Demo", tags=[], duration=timedelta(minutes=5))

    NO_SWITCH = Benchmark("configuration/no_switch", "No Switch", tags=[])


    BASE_TWO_CLIENTS = benchmark_scalability(num_nodes=3)
    BASE_ALL_CLIENTS = benchmark_scalability(num_nodes=12)

    # 3 nodes and all nodes (12) defined above already
    SCALABILITY_REMAINING_CLIENTS = [
        benchmark_scalability(num_nodes=extra_nodes) for extra_nodes in range(4, 12)
    ]
    SCALABILITY_ALL = [BASE_TWO_CLIENTS, *SCALABILITY_REMAINING_CLIENTS, BASE_ALL_CLIENTS]

    _FAULT_TIMING_SETTINGS = {
        'duration': timedelta(minutes=15),
        'fault_interval': timedelta(minutes=10),
        'fault_duration': timedelta(minutes=1),
    }

    SOFTWARE_FAULT_SLAVE = Benchmark(
        "fault/software/slave", "Software Fault (Slave)",
        tags=[ProfileTags.CATEGORY_FAULT, ProfileTags.FAULT_SOFTWARE, ProfileTags.FAULT_LOCATION_SLAVE],
        num_machines=3,
        ptp_keepalive=True,
        fault_software=True,
        fault_location=EndpointType.PRIMARY_SLAVE,
        **_FAULT_TIMING_SETTINGS,
    )

    HARDWARE_FAULT_SWITCH = Benchmark(
        "fault/hardware/switch", "Hardware Fault (Switch)",
        tags=[ProfileTags.CATEGORY_FAULT, ProfileTags.FAULT_HARDWARE, ProfileTags.FAULT_LOCATION_SWITCH],
        num_machines=3,
        fault_hardware=True,
        fault_location=EndpointType.SWITCH,
        **_FAULT_TIMING_SETTINGS,
    )

    HARDWARE_FAULT_SLAVE = Benchmark(
        "fault/hardware/slave", "Hardware Fault (Slave)",
        tags=[ProfileTags.CATEGORY_FAULT, ProfileTags.FAULT_HARDWARE, ProfileTags.FAULT_LOCATION_SLAVE],
        num_machines=3,
        fault_hardware=True,
        fault_location=EndpointType.PRIMARY_SLAVE,
        fault_ssh_keepalive=True,
        analyze_limit_permissible_clock_steps=None,
        **_FAULT_TIMING_SETTINGS,
    )

    HARDWARE_FAULT_MASTER = Benchmark(
        "fault/hardware/master", "Hardware Fault (Master)",
        tags=[ProfileTags.CATEGORY_FAULT, ProfileTags.FAULT_HARDWARE, ProfileTags.FAULT_LOCATION_MASTER],
        num_machines=3,
        fault_hardware=True,
        fault_location=EndpointType.MASTER,
        fault_ssh_keepalive=True,
        analyze_limit_permissible_clock_steps=None,
        **_FAULT_TIMING_SETTINGS,
    )

    HARDWARE_FAULT_MASTER_FAILOVER = Benchmark(
        "fault/hardware/master_failover", "Hardware Fault (Failover)",
        tags=[ProfileTags.CATEGORY_FAULT, ProfileTags.FAULT_HARDWARE, ProfileTags.FAULT_LOCATION_MASTER],
        num_machines=3,
        fault_hardware=True,
        fault_failover=True,
        # fault_interval=timedelta(minutes=5),
        # fault_duration=timedelta(minutes=2.5),
        fault_location=EndpointType.MASTER,
        fault_ssh_keepalive=True,
        analyze_limit_permissible_clock_steps=None,
        **_FAULT_TIMING_SETTINGS,
    )

    RESOURCE_CONSUMPTION = Benchmark(
        "resource_consumption", "Resource Consumption",
        tags=[ProfileTags.CATEGORY_RESOURCE_CONSUMPTION],
        monitor_resource_consumption=True,
    )


    @staticmethod
    def resource_contention(component: ResourceContentionComponent, type: ResourceContentionType, load_level: int):
        """Create a network contention benchmark for a target bandwidth.
        :param component: Which component is being artificially loaded.
        :param type: How the load should be generated.
        :param load_level: Percentage of load of (assumed GBit) interface to apply.
        """

        benchmark_options = {
            'id': f"load/{component.id}_{type.id}/load_{load_level}",
        }
        tags = [ProfileTags.CATEGORY_LOAD, component.tag, type.tag]

        # Set up component specific values
        if component == ResourceContentionComponent.NET:
            benchmark_options.update(
                artificial_load_network=load_level * 1000 // 100, # 1000 Mbit/s = 1 Gbit/s, load_level is percentage
            )
        elif component == ResourceContentionComponent.CPU:
            benchmark_options.update(
                artificial_load_cpu=load_level
            )
        else:
            raise RuntimeError(f"Unknown resource contention component: {component}")

        # Setup isolation specific values.
        if type == ResourceContentionType.UNPRIORITIZED:
            pass
        elif type == ResourceContentionType.PRIORITIZED:
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
            else:
                raise RuntimeError(f"Unknown contention component: {component}")

        elif type == ResourceContentionType.ISOLATED:
            if component == ResourceContentionComponent.NET:
                benchmark_options.update(
                    artificial_load_network_secondary_interface=True,
                    artificial_load_network_dscp_priority='cs1',
                    # We also use low traffic priority to avoid disrupting SSH and database connections.
                    # CS1 is low priority traffic: https://en.wikipedia.org/wiki/Differentiated_services#Class_Selector
                )
            elif component == ResourceContentionComponent.CPU:
                benchmark_options.update(
                    artificial_load_cpu_restrict_cores=True,
                )
            else:
                raise RuntimeError(f"Unknown contention component: {component}")

        else:
            raise RuntimeError(f"Unknown network contention type: {type}")

        return Benchmark(
            name=f"{type.name} {component.name} {load_level}% Load",
            tags=tags,
            **benchmark_options,
        )

    @staticmethod
    def resource_contention_aux(id: str,  name: str, options: List[str]):
        return Benchmark(
            id=f"load/{ResourceContentionComponent.AUX.id}_{id}/load_100",
            name=f"Unprioritized {name} 100% Load",
            tags=[ProfileTags.CATEGORY_LOAD, ProfileTags.ISOLATION_UNPRIORITIZED, ProfileTags.COMPONENT_AUX],
            artificial_load_aux=True,
            artificial_load_aux_options=options,
        )



    @staticmethod
    def config_test(configuration: PTPConfig, id_label: str, title_label: str, extra_tags: List[str]):
        return Benchmark(
            f"config/{id_label}",
            f"Config {title_label}",
            tags=[ProfileTags.CATEGORY_CONFIGURATION, *extra_tags],
            ptp_config=configuration,
        )

    @staticmethod
    def all_by_tags(*tags) -> List[Benchmark]:
        return [benchmark for benchmark in BenchmarkDB.all() if all(search_tag in benchmark.tags for search_tag in tags)]

BenchmarkDB.register_all(
    BenchmarkDB.BASE, BenchmarkDB.TEST, BenchmarkDB.DEMO,
    BenchmarkDB.BASE_TWO_CLIENTS, BenchmarkDB.BASE_ALL_CLIENTS, *BenchmarkDB.SCALABILITY_REMAINING_CLIENTS,
    BenchmarkDB.SOFTWARE_FAULT_SLAVE,
    BenchmarkDB.HARDWARE_FAULT_SWITCH, BenchmarkDB.HARDWARE_FAULT_SLAVE, BenchmarkDB.HARDWARE_FAULT_MASTER,
    BenchmarkDB.HARDWARE_FAULT_MASTER_FAILOVER,
    BenchmarkDB.NO_SWITCH,
    BenchmarkDB.RESOURCE_CONSUMPTION,
)

for component in [ResourceContentionComponent.NET, ResourceContentionComponent.CPU]:
    for load_level in [10, 20, 33, 50, 66, 80, 90, 100]:
        BenchmarkDB.register(BenchmarkDB.resource_contention(component, ResourceContentionType.UNPRIORITIZED, load_level=load_level))
        BenchmarkDB.register(BenchmarkDB.resource_contention(component, ResourceContentionType.UNPRIORITIZED, load_level=load_level))

    # Just one prioritized and isolated benchmark for now at 100%
    BenchmarkDB.register_all(BenchmarkDB.resource_contention(component, ResourceContentionType.PRIORITIZED, load_level=100))
    BenchmarkDB.register_all(BenchmarkDB.resource_contention(component, ResourceContentionType.ISOLATED, load_level=100))

# Auxiliary stresses (Unisolated, Full Load)
BenchmarkDB.register_all(
    BenchmarkDB.resource_contention_aux("alarm", "Alarm", options=["--alarm", "4"]),
    BenchmarkDB.resource_contention_aux("cache", "Cache", options=["--cache", "4"]),
    BenchmarkDB.resource_contention_aux("cyclic", "Cyclic", options=["--cyclic", "1"]),
    BenchmarkDB.resource_contention_aux("memory", "Memory", options=["--stream", "4"]),
    BenchmarkDB.resource_contention_aux("switch", "Switch", options=["--switch", "4"]),
    BenchmarkDB.resource_contention_aux("timer", "Timer", options=["--timer", "4"]),
)

# Different configurations
for interval in [3, 2, 1, 0, -1, -2, -3, -4, -5, -6, -7]:
    BenchmarkDB.register_all(
        BenchmarkDB.config_test(
            PTPConfig(
                log_sync_interval=interval,
                log_delayreq_interval=interval,
            ),
            id_label=f"interval/{interval:+}",
            title_label=f"Interval {interval:+}",
            extra_tags=[ProfileTags.CONFIGURATION_INTERVAL],
        )
    )
