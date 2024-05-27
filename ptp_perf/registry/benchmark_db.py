from datetime import timedelta
from typing import List

from ptp_perf import config
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.profiles.base_profile import ProfileTags
from ptp_perf.profiles.benchmark import Benchmark, PTPConfig
from ptp_perf.profiles.taxonomy import ResourceContentionType, ResourceContentionComponent
from ptp_perf.registry.base_registry import BaseRegistry
from ptp_perf.util import str_join


# Some benchmark recipies
def benchmark_scalability(num_nodes: int):
    return Benchmark(
        f"scalability/1_to_{num_nodes - 1}", f"{num_nodes} Nodes", tags=[],
        num_machines=num_nodes,
        monitor_resource_consumption=True,
        description="The benchmark is used to measure the performance of the cluster with different numbers of nodes. "
                    "Each benchmark includes one master and the remaining nodes are slaves. "
                    "A set of scalability benchmarks can show the scalability trend. "
                    "System resource consumption is monitored during the benchmark. "
    )


class BenchmarkDB(BaseRegistry[Benchmark]):

    BASE = Benchmark(
        "base", "Baseline", tags=[],
        description="The base benchmark to compare other benchmarks against. "
                    "It is the default benchmark for all new clusters. "
                    "It is used to measure the performance of the cluster without any additional load or faults. "
    )
    TEST = Benchmark(
        "test/test", "Test", tags=[], duration=timedelta(minutes=1),
        description="A test benchmark to quickly verify the cluster is working correctly. "
                    "It is identical to the base benchmark but runs for a shorter duration."
    )

    DEMO = Benchmark(
        "test/demo", "Demo", tags=[], duration=timedelta(minutes=5),
        description="A demo benchmark to quickly assess the capabilities of the cluster. "
                    "It is identical to the base benchmark but runs for a shorter duration."
    )

    NO_SWITCH = Benchmark(
        "configuration/no_switch", "No Switch", tags=[],
        description="A benchmark to measure the performance of the cluster without a network switch. "
                    "The configuration is identical to the baseline, "
                    "the user is expected to rewire the cluster appropriately before running this benchmark. "
    )


    BASE_AS_SCALABILITY = benchmark_scalability(num_nodes=2)
    BASE_TWO_CLIENTS = benchmark_scalability(num_nodes=3)
    BASE_ALL_CLIENTS = benchmark_scalability(num_nodes=12)

    # 3 nodes and all nodes (12) defined above already
    SCALABILITY_REMAINING_CLIENTS = [
        benchmark_scalability(num_nodes=extra_nodes) for extra_nodes in range(4, 12)
    ]
    SCALABILITY_ALL = [BASE_AS_SCALABILITY, BASE_TWO_CLIENTS, *SCALABILITY_REMAINING_CLIENTS, BASE_ALL_CLIENTS]

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
        description="A benchmark to measure the performance of the cluster with a software fault on a slave. "
                    "The software fault is created by killing and restarting the PTP daemon on the slave machine. "
                    "A second slave is used as a control node to check whether it is affected by the fault. "
                    "The fault occurs 10 minutes into the benchmark and lasts for 1 minute."
    )

    HARDWARE_FAULT_SWITCH = Benchmark(
        "fault/hardware/switch", "Hardware Fault (Switch)",
        tags=[ProfileTags.CATEGORY_FAULT, ProfileTags.FAULT_HARDWARE, ProfileTags.FAULT_LOCATION_SWITCH],
        num_machines=3,
        fault_hardware=True,
        fault_location=EndpointType.SWITCH,
        **_FAULT_TIMING_SETTINGS,
        description="A benchmark to measure the performance of the cluster with a hardware fault on the network switch. "
                    "The hardware fault is created by turning off the power to the network switch using a smart PDU "
                    "(check the documentation on how to register it with PTP-Perf). "
                    "It is expected that both the primary and the secondary slave are affected by the network outage. "
                    "The fault occurs 10 minutes into the benchmark and lasts for 1 minute."
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
        description="A benchmark to measure the performance of the cluster with a hardware fault on a slave. "
                    "The hardware fault is created by turning off the power to the slave machine using a smart PDU "
                    "(check the documentation on how to register it with PTP-Perf). "
                    "A second slave is used as a control node to check whether it is affected by the fault. "
                    "The fault occurs 10 minutes into the benchmark and lasts for 1 minute."
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
        description="A benchmark to measure the performance of the cluster with a hardware fault on the master. "
                    "The hardware fault is created by turning off the power to the master machine using a smart PDU "
                    "(check the documentation on how to register it with PTP-Perf). "
                    "A second slave is used as a control node, it is expected to also be affected by the fault. "
                    "The fault occurs 10 minutes into the benchmark and lasts for 1 minute."
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
        description="A benchmark to measure the performance of the cluster with a hardware fault on the master "
                    "but with a failover master on the secondary slave that will take over once the primary master fails. "
                    "The fault occurs 10 minutes into the benchmark and lasts for 1 minute. "
                    "After the fault is resolved, the failover master will be demoted back to a slave, allowing the primary master to take over again. "
                    "The benchmark is expected to show a seamless transition between the primary and failover masters. "
                    "The hardware fault is created by turning off the power to the master machine using a smart PDU "
                    "(check the documentation on how to register it with PTP-Perf). "
    )

    RESOURCE_CONSUMPTION = Benchmark(
        "resource_consumption", "Resource Consumption",
        tags=[ProfileTags.CATEGORY_RESOURCE_CONSUMPTION],
        monitor_resource_consumption=True,
        description="A benchmark to measure the resource consumption of the PTP applications on each node. "
                    "Collected metrics include CPU usage, memory usage, network traffic, and clock synchronization statistics. "
                    "The benchmark runs for 15 minutes to collect a sufficient amount of data. "
                    "It is otherwise identical to the base benchmark."
    )


    @staticmethod
    def resource_contention(component: ResourceContentionComponent, type: ResourceContentionType, load_level: int):
        """Create a network contention benchmark for a target bandwidth.
        :param component: Which component is being artificially loaded.
        :param type: How the load should be generated.
        :param load_level: Percentage of load of (assumed GBit) interface to apply.
        """
        extra_description = ""

        benchmark_options = {
            'id': f"load/{component.id}_{type.id}/load_{load_level}",
        }
        tags = [ProfileTags.CATEGORY_LOAD, component.tag, type.tag]

        # Set up component specific values
        if component == ResourceContentionComponent.NET:
            target_bandwidth = load_level * 1000 // 100 # 1000 Mbit/s = 1 Gbit/s, load_level is percentage
            benchmark_options.update(
                artificial_load_network=target_bandwidth,
            )
            extra_description += (f"The network load is generated using iPerf, a network performance testing tool. "
                                  f"The target bandwidth is set to {load_level}% of the network interface capacity. "
                                  f" A GigaBit Ethernet network interface is assumed, so the load is {target_bandwidth} Mbit/s.")
        elif component == ResourceContentionComponent.CPU:
            benchmark_options.update(
                artificial_load_cpu=load_level
            )
            extra_description += (f"The CPU load is generated using Stress-NG, a stress testing tool. "
                                  f"The target CPU load is set to {load_level}% of the CPU capacity. "
                                  f"Each node in the cluster uses the number of cores specified in the machine configuration. ")
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
                extra_description += ("The network traffic generated by iPerf is marked with a low priority DSCP value. "
                                      "This should allow the network to prioritize PTP traffic over the generated network traffic, "
                                      "which is expected to improve the PTP performance under network contention. ")
            elif component == ResourceContentionComponent.CPU:
                benchmark_options.update(
                    artificial_load_cpu_scheduler="idle",
                    # Cannot set nice priority, so use scheduler idle instead.
                    # Nice priority +19 is lowest: https://www.man7.org/linux/man-pages/man7/sched.7.html
                )
                extra_description += ("The Stress-NG CPU load is generated using the idle scheduler, "
                                      "which is expected to give priority to the PTP applications over the generated CPU load. "
                                      "This is expected to improve the PTP performance under CPU contention. ")
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
                extra_description += ("The network traffic generated by iPerf uses a secondary network interface that is different from the network interface used by PTP. "
                                      "The secondary network interface is specified in the machine configuration. "
                                      "This will isolate the network traffic from the PTP applications, "
                                      "which is expected to improve the PTP performance under network contention. "
                                      "The network traffic is also marked with a low priority DSCP value, "
                                      "to avoid disrupting SSH and database connections as well as other traffic on the secondary interface. ")
            elif component == ResourceContentionComponent.CPU:
                benchmark_options.update(
                    artificial_load_cpu_restrict_cores=True,
                )
                extra_description += ("The Stress-NG CPU load is generated using task affinity to restrict the CPU cores used by the load. "
                                      "PTP is thus open to use all the other cores. "
                                      "This will isolate the CPU load from the PTP applications, "
                                      "which is expected to improve the PTP performance under CPU contention. ")
            else:
                raise RuntimeError(f"Unknown contention component: {component}")

        else:
            raise RuntimeError(f"Unknown network contention type: {type}")

        return Benchmark(
            name=f"{type.name} {component.name} {load_level}% Load",
            tags=tags,
            **benchmark_options,
            description=f"A benchmark to measure the performance of the cluster under different levels of {component} contention. "
                        f"The {component} is loaded to {load_level}% of its capacity. "
                        f"This is expected to affect the performance of the PTP applications running on the cluster. "
                        f"{extra_description}"
        )

    @staticmethod
    def resource_contention_aux(id: str,  name: str, options: List[str]):
        return Benchmark(
            id=f"load/{ResourceContentionComponent.AUX.id}_{id}/load_100",
            name=f"Unprioritized {name} 100% Load",
            tags=[ProfileTags.CATEGORY_LOAD, ProfileTags.ISOLATION_UNPRIORITIZED, ProfileTags.COMPONENT_AUX],
            artificial_load_aux=True,
            artificial_load_aux_options=options,
            description=f"A benchmark to measure the performance of the cluster under auxiliary contention. "
                        f"Specifically, this benchmark tests {name} contention. "
                        f"The auxiliary contention is generated using Stress-NG, a stress testing tool. "
                        f"Refer to the Stress-NG documentation for more information on the specific options used. "
                        f"The Stress-NG options are: {str_join(options, ' ')}."
        )



    @staticmethod
    def config_test(configuration: PTPConfig, id_label: str, title_label: str, extra_tags: List[str]):
        return Benchmark(
            f"config/{id_label}",
            f"Config {title_label}",
            tags=[ProfileTags.CATEGORY_CONFIGURATION, *extra_tags],
            ptp_config=configuration,
            description="A benchmark to test the performance of the cluster with a specific PTP configuration. "
                        "Currently, this is only used to modify the frequency of PTP synchronization/path delay/announce messages. "
                        "Refer to PTP documentation on the meaning of these message intervals. "
        )

    @staticmethod
    def all_by_tags(*tags) -> List[Benchmark]:
        return [benchmark for benchmark in BenchmarkDB.all() if all(search_tag in benchmark.tags for search_tag in tags)]

BenchmarkDB.register_all(
    BenchmarkDB.BASE, BenchmarkDB.TEST, BenchmarkDB.DEMO,
    BenchmarkDB.BASE_AS_SCALABILITY, BenchmarkDB.BASE_TWO_CLIENTS, BenchmarkDB.BASE_ALL_CLIENTS,
    *BenchmarkDB.SCALABILITY_REMAINING_CLIENTS,
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
