import dataclasses
import itertools
from dataclasses import dataclass
from datetime import timedelta

from ptp_perf.machine import Cluster, Machine, PluginSettings
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.util import ImmediateException, str_join


# We can define options that we apply to multiple machines in dictionaries to reduce redundancy.
# We can then apply these options to the machines by unpacking the dictionary into the Machine constructor.
# This is an example of the DRY principle.
PTP_SLAVE_SETTINGS = {
    # The initial clock offset is set to -1 minute for the slaves to ensure that their local clock has a predictable offset from the master at the beginning of the benchmark.
    'initial_clock_offset': timedelta(minutes=-1),
}

# We can also define more dictionaries to group options according to types of nodes in our cluster.
RASPBERRY_PI_4_PTP_SETTINGS = {
    # The Raspberry Pi 4 uses the eth0 interface for PTP, does not use phc2sys, and uses software timestamping.
    'ptp_interface': 'eth0',
    'ptp_use_phc2sys': False,
    'ptp_software_timestamping': True,
}

# We define the actual machines with their roles and settings.
# Each machine needs to be accessible via SSH using passwordless authentication via the {address} specified and have the tested PTP vendors installed.
# The local copy of the repository will be stored in the {remote_root} directory using rsync.
# The RPI06 machine is the master of the cluster, and it has the iperf server enabled for network load benchmarks.
# We use the 10.0.0.0/24 subnet for the (isolated) PTP network and the 192.168.1.0/24 subnet as the secondary network for auxiliary traffic.
# The stress-ng tool is used to generate CPU load on the machine for CPU load benchmarks. By default, it uses the specified number of CPUs without restrictions in the unisolated case.
# It can be restricted to specific cores for the CPU load isolated benchmark, in this case cores 2 and 3. That leaves cores 0 and 1 free for the PTP daemon.
MACHINE_RPI06 = Machine(
    id="rpi06", address="rpi06", remote_root="/home/rpi/ptp-perf",
    ptp_address="10.0.0.6",
    endpoint_type=EndpointType.MASTER,
    **RASPBERRY_PI_4_PTP_SETTINGS,
    plugin_settings=PluginSettings(
        iperf_server=True, iperf_address="10.0.0.6", iperf_secondary_address="192.168.1.106",
        stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)
# The RPI07 machine is the primary slave of the cluster, used for calculating statistics and analyzing the performance of the clock synchronization.
MACHINE_RPI08 = Machine(
    id="rpi08", address="rpi08", remote_root="/home/rpi/ptp-perf",
    ptp_address="10.0.0.8",
    **PTP_SLAVE_SETTINGS,
    endpoint_type=EndpointType.PRIMARY_SLAVE,
    **RASPBERRY_PI_4_PTP_SETTINGS,
    plugin_settings=PluginSettings(
        iperf_server=False, iperf_address="10.0.0.8", iperf_secondary_address="192.168.1.108",
        stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)
# The RPI08 machine is the secondary slave of the cluster.
# It is used as a failover master during the master failover fault benchmark, and as a comparison slave node during other fault benchmarks.
MACHINE_RPI07 = Machine(
    id="rpi07", address="rpi07", remote_root="/home/rpi/ptp-perf",
    ptp_address="10.0.0.7",
    **PTP_SLAVE_SETTINGS,
    endpoint_type=EndpointType.SECONDARY_SLAVE,
    **RASPBERRY_PI_4_PTP_SETTINGS,
    plugin_settings=PluginSettings(
        iperf_server=False, iperf_address="10.0.0.7", iperf_secondary_address="192.168.1.107",
        stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)
# We group the machines into a cluster for easier management and configuration.
# The cluster is what is passed to the orchestrator to run the benchmark on a specific set of nodes.
CLUSTER_PI = Cluster(
    id="rpi-4",
    name="Raspberry Pi 4",
    machines=[
        MACHINE_RPI06, MACHINE_RPI08, MACHINE_RPI07
    ],
    fault_hardware_supported=True,
)

# We can define more clusters with different configurations and machines.
# The Raspberry Pi 5 machines have different PTP settings compared to the Raspberry Pi 4 machines.
RASPBERRY_PI_5_PTP_SETTINGS = {
    'ptp_interface': 'eth0',
    'ptp_use_phc2sys': False,
    'ptp_software_timestamping': False,
}
# We have the same overall layout for all clusters, with a master, a primary slave, a secondary slave
# and any number of tertiary slaves for additional nodes in the scalability benchmark.
MACHINE_RPI56 = Machine(
    id="rpi56", address="rpi56", remote_root="/home/rpi/ptp-perf",
    ptp_address="10.0.0.56",
    endpoint_type=EndpointType.MASTER,
    **RASPBERRY_PI_5_PTP_SETTINGS,
    plugin_settings=PluginSettings(
        iperf_server=True, iperf_address="10.0.0.56", iperf_secondary_address="192.168.1.156",
        stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)
MACHINE_RPI58 = Machine(
    id="rpi58", address="rpi58", remote_root="/home/rpi/ptp-perf",
    ptp_address="10.0.0.58",
    **PTP_SLAVE_SETTINGS,
    endpoint_type=EndpointType.PRIMARY_SLAVE,
    **RASPBERRY_PI_5_PTP_SETTINGS,
    plugin_settings=PluginSettings(
        iperf_server=False, iperf_address="10.0.0.58", iperf_secondary_address="192.168.1.158",
        stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)
MACHINE_RPI57 = Machine(
    id="rpi57", address="rpi57", remote_root="/home/rpi/ptp-perf",
    ptp_address="10.0.0.57",
    **PTP_SLAVE_SETTINGS,
    endpoint_type=EndpointType.SECONDARY_SLAVE,
    **RASPBERRY_PI_5_PTP_SETTINGS,
    plugin_settings=PluginSettings(
        iperf_server=False, iperf_address="10.0.0.57", iperf_secondary_address="192.168.1.157",
        stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)
CLUSTER_PI5 = Cluster(
    id="rpi-5",
    name="Raspberry Pi 5",
    machines=[
        MACHINE_RPI56, MACHINE_RPI58, MACHINE_RPI57
    ],
    fault_hardware_supported=True,
)

# New boards
PETALINUX_PTP_SETTINGS = {
    'ptp_interface': 'end0',
    'ptp_use_phc2sys': False,
    'ptp_software_timestamping': False,
}
MACHINE_PETALINUX01 = Machine(
    id="petalinux01", address="petalinux01", remote_root="/home/rpi/ptp-perf",
    ptp_address="10.0.0.81",
    endpoint_type=EndpointType.MASTER,
    **PETALINUX_PTP_SETTINGS,
    plugin_settings=PluginSettings(
        iperf_server=True, iperf_address="10.0.0.81", iperf_secondary_address="192.168.1.181",
        stress_ng_cpus=2, stress_ng_cpu_restrict_cores="1")
)
MACHINE_PETALINUX02 = Machine(
    id="petalinux02", address="petalinux02", remote_root="/home/rpi/ptp-perf",
    ptp_address="10.0.0.82",
    **PTP_SLAVE_SETTINGS,
    endpoint_type=EndpointType.PRIMARY_SLAVE,
    **PETALINUX_PTP_SETTINGS,
    plugin_settings=PluginSettings(
        iperf_server=False, iperf_address="10.0.0.82", iperf_secondary_address="192.168.1.182",
        stress_ng_cpus=2, stress_ng_cpu_restrict_cores="1")
)
MACHINE_PETALINUX03 = Machine(
    id="petalinux03", address="petalinux03", remote_root="/home/rpi/ptp-perf",
    ptp_address="10.0.0.83",
    **PTP_SLAVE_SETTINGS,
    endpoint_type=EndpointType.SECONDARY_SLAVE,
    **PETALINUX_PTP_SETTINGS,
    plugin_settings=PluginSettings(
        iperf_server=False, iperf_address="10.0.0.83", iperf_secondary_address="192.168.1.183",
        stress_ng_cpus=2, stress_ng_cpu_restrict_cores="1")
)
MACHINE_PETALINUX04 = Machine(
    id="petalinux04", address="petalinux04", remote_root="/home/rpi/ptp-perf",
    ptp_address="10.0.0.84",
    **PTP_SLAVE_SETTINGS,
    endpoint_type=EndpointType.TERTIARY_SLAVE,
    **PETALINUX_PTP_SETTINGS,
    plugin_settings=PluginSettings(
        iperf_server=False, iperf_address="10.0.0.84", iperf_secondary_address="192.168.1.184",
        stress_ng_cpus=2, stress_ng_cpu_restrict_cores="1")
)
CLUSTER_PETALINUX = Cluster(
    id="petalinux",
    name="Xilinx",
    machines=[
        MACHINE_PETALINUX01, MACHINE_PETALINUX02, MACHINE_PETALINUX03, MACHINE_PETALINUX04,
    ],
    fault_hardware_supported=False,
)

# We also have a cluster of Jetson TK-1 boards.
# The {python_executable} field can be used to specify e.g. a virtual environment to use instead of the default system interpreter.
MACHINE_TK1_1 = Machine(
    id="tk1-1", address="tk1-1", remote_root="/home/ubuntu/ptp-perf",
    ptp_address="10.0.0.71",
    endpoint_type=EndpointType.MASTER,
    ptp_interface='enp1s0',
    ptp_use_phc2sys=False,
    ptp_software_timestamping=True,
    python_executable='python3.11',
    shutdown_delay=timedelta(minutes=1),
    plugin_settings=PluginSettings(
        iperf_server=True, iperf_address="10.0.0.81", iperf_secondary_address="192.168.1.171",
        stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)
MACHINE_TK1_2 = Machine(
    id="tk1-2", address="tk1-2", remote_root="/home/ubuntu/ptp-perf",
    ptp_address="10.0.0.72",
    **PTP_SLAVE_SETTINGS,
    endpoint_type=EndpointType.PRIMARY_SLAVE,
    ptp_interface='eth0',
    ptp_use_phc2sys=False,
    ptp_software_timestamping=True,
    python_executable='python3.11',
    shutdown_delay=timedelta(minutes=1),
    plugin_settings=PluginSettings(
        iperf_server=False, iperf_address="10.0.0.82", iperf_secondary_address="192.168.1.172",
        stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)
CLUSTER_TK1 = Cluster(
    id="tk-1",
    name="Jetson TK-1",
    machines=[
        MACHINE_TK1_1, MACHINE_TK1_2
    ],
    fault_hardware_supported=False,
)

# This is our local orchestrator machine, which is used to run the benchmark and collect the results.
# It does not require the PTP settings as it is not part of the PTP network.
MACHINE_RPISERV = Machine(
    id="rpi-serv", address="rpi-serv", remote_root="/home/rpi/ptp-perf",
    ptp_address="0.0.0.0",
    endpoint_type=EndpointType.ORCHESTRATOR,
    ptp_interface="",
)
CLUSTER_RPI_SERV = Cluster(
    id="rpi-serv",
    name='RPI Server',
    machines=[
        MACHINE_RPISERV
    ]
)

# These are our network switches, which are used to connect the PTP nodes in the cluster.
# If they have a machine definition, they can be triggered via smart PDUs to simulate network faults.
MACHINE_SWITCH = Machine(
    id="switch", endpoint_type=EndpointType.SWITCH,
    address=None, ptp_address=None, ptp_interface=None,
)
MACHINE_SWITCH2 = Machine(
    id="switch2", endpoint_type=EndpointType.SWITCH,
    address=None, ptp_address=None, ptp_interface=None,
)

# We have a special cluster that combines all nodes from all our previous clusters.
# This is used for the scalability benchmark to test the performance of the PTP network with a large number of nodes.
def create_big_bad_cluster_machines():
    machines=[
        dataclasses.replace(
            machine,
            endpoint_type=EndpointType.TERTIARY_SLAVE,
            initial_clock_offset=timedelta(minutes=-1),
            id=f"bb-{machine.id}"
        ) for machine in itertools.chain(
            CLUSTER_PI5.machines, CLUSTER_PETALINUX.machines, CLUSTER_PI.machines, CLUSTER_TK1.machines,
        )
    ]
    machines[0].endpoint_type = EndpointType.MASTER
    machines[0].initial_clock_offset = None
    machines[1].endpoint_type = EndpointType.PRIMARY_SLAVE
    machines[2].endpoint_type = EndpointType.SECONDARY_SLAVE

    return machines

MACHINES_BIG_BAD_CLUSTER = create_big_bad_cluster_machines()
CLUSTER_BIG_BAD = Cluster(
    id="big-bad",
    name="Big Bad Cluster",
    machines=create_big_bad_cluster_machines(),
)

machines = {
    machine.id: machine for machine in [
        MACHINE_RPI06, MACHINE_RPI07, MACHINE_RPI08,
        MACHINE_RPI56, MACHINE_RPI57, MACHINE_RPI58,
        MACHINE_RPISERV, MACHINE_SWITCH,
        MACHINE_SWITCH2,
        MACHINE_PETALINUX01, MACHINE_PETALINUX02, MACHINE_PETALINUX03, MACHINE_PETALINUX04,
        MACHINE_TK1_1, MACHINE_TK1_2,
        *MACHINES_BIG_BAD_CLUSTER,
    ]
}
ANALYZED_MACHINES = [
    MACHINE_RPI06, MACHINE_RPI07, MACHINE_RPI08,
    MACHINE_RPI56, MACHINE_RPI57, MACHINE_RPI58,
    MACHINE_PETALINUX01, MACHINE_PETALINUX02, MACHINE_PETALINUX03, MACHINE_PETALINUX04,
    MACHINE_TK1_1, MACHINE_TK1_2,
]

clusters = {
    cluster.id: cluster for cluster in [
        CLUSTER_PI, CLUSTER_PI5, CLUSTER_PETALINUX, CLUSTER_TK1, CLUSTER_RPI_SERV, CLUSTER_BIG_BAD
    ]
}
ANALYZED_CLUSTERS = [CLUSTER_PI, CLUSTER_PI5, CLUSTER_PETALINUX, CLUSTER_TK1, CLUSTER_BIG_BAD]
ANALYZED_CLUSTER_IDS = [cluster.id for cluster in ANALYZED_CLUSTERS]

@dataclass
class Configuration:
    cluster: Cluster = None

    def subset_cluster_configuration(self, num_machines: int):
        return Configuration(
            cluster=self.cluster.subset_cluster(num_machines)
        )


def verify(configuration: Configuration):
    """Verify that the configuration is valid."""

    # Check unique ids
    ids = [machine.id for machine in configuration.cluster.machines]
    if len(set(ids)) != len(ids):
        raise RuntimeError("The configuration contains duplicate machine ids.")


def get_configuration_by_cluster_name(name: str) -> Configuration:
    try:
        cluster = clusters[name]
    except KeyError:
        raise ImmediateException(f"Configuration not found: {name} (from {str_join(clusters.keys())})")

    configuration = Configuration()
    configuration.cluster = cluster

    verify(configuration)
    return configuration

