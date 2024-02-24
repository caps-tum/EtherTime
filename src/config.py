import copy
from dataclasses import dataclass
from datetime import timedelta

from machine import Cluster, Machine, PluginSettings
from util import ImmediateException, str_join

RASPBERRY_PI_PTP_SETTINGS = {
    'ptp_interface': 'eth0',
    'ptp_use_phc2sys': False,
    'ptp_software_timestamping': True,
}

PTP_SLAVE_SETTINGS = {
    'ptp_master': False,
    'initial_clock_offset': timedelta(minutes=-1),
}

MACHINE_RPI06 = Machine(
    id="rpi06", address="rpi06", remote_root="/home/rpi/ptp-perf",
    ptp_master=True,
    **RASPBERRY_PI_PTP_SETTINGS,
    plugin_settings=PluginSettings(
        iperf_server=True, iperf_address="10.0.0.6", iperf_secondary_address="192.168.1.106",
        stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)
MACHINE_RPI08 = Machine(
    id="rpi08", address="rpi08", remote_root="/home/rpi/ptp-perf",
    **PTP_SLAVE_SETTINGS,
    **RASPBERRY_PI_PTP_SETTINGS,
    plugin_settings=PluginSettings(
        iperf_server=False, iperf_address="10.0.0.8", iperf_secondary_address="192.168.1.108",
        stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)
MACHINE_RPI07 = Machine(
    id="rpi07", address="rpi07", remote_root="/home/rpi/ptp-perf",
    **PTP_SLAVE_SETTINGS,
    **RASPBERRY_PI_PTP_SETTINGS,
    plugin_settings=PluginSettings(iperf_server=False, iperf_address=None, stress_ng_cpus=4,
                                   stress_ng_cpu_restrict_cores="2,3")
)
MACHINE_RPISERV = Machine(
    id="rpi-serv", address="rpi-serv", remote_root="/home/rpi/ptp-perf",
    ptp_interface="",
)

machines = {
    machine.id: machine for machine in [MACHINE_RPI06, MACHINE_RPI07, MACHINE_RPI08, MACHINE_RPISERV]
}

CLUSTER_PI = Cluster(
    id="Pi Cluster",
    machines=[
        MACHINE_RPI06, MACHINE_RPI08
    ]
)
CLUSTER_RPI_SERV = Cluster(
    id="rpi-serv",
    machines=[
        MACHINE_RPISERV
    ]
)
CLUSTER_3_PI = Cluster(
    id="3-Pi",
    machines=[MACHINE_RPI06, MACHINE_RPI08, MACHINE_RPI07],
)

clusters = {
    cluster.id: cluster for cluster in [CLUSTER_PI, CLUSTER_RPI_SERV, CLUSTER_3_PI]
}


@dataclass
class Configuration:
    cluster: Cluster = None
    machine: Machine = None


# current_configuration = Configuration()

# Currently we default to the first (only) defined cluster
# current_configuration.cluster = clusters["Pi Cluster"]
# current_configuration.cluster = clusters["3-Pi"]


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


def subset_cluster(configuration: Configuration, num_machines: int) -> Configuration:
    new_config = copy.deepcopy(configuration)
    new_config.cluster = new_config.cluster[0:num_machines]
    return new_config
