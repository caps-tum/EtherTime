import copy
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from ptp_perf.machine import Cluster, Machine, PluginSettings
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.util import ImmediateException, str_join

RASPBERRY_PI_PTP_SETTINGS = {
    'ptp_interface': 'eth0',
    'ptp_use_phc2sys': False,
    'ptp_software_timestamping': True,
}

PTP_SLAVE_SETTINGS = {
    'ptp_force_master': False,
    'ptp_force_slave': True,
    'initial_clock_offset': timedelta(minutes=-1),
}

MACHINE_RPI06 = Machine(
    id="rpi06", address="rpi06", remote_root="/home/rpi/ptp-perf",
    ptp_force_master=True,
    endpoint_type=EndpointType.MASTER,
    **RASPBERRY_PI_PTP_SETTINGS,
    ptp_priority_1=1,
    plugin_settings=PluginSettings(
        iperf_server=True, iperf_address="10.0.0.6", iperf_secondary_address="192.168.1.106",
        stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)
MACHINE_RPI08 = Machine(
    id="rpi08", address="rpi08", remote_root="/home/rpi/ptp-perf",
    **PTP_SLAVE_SETTINGS,
    endpoint_type=EndpointType.PRIMARY_SLAVE,
    **RASPBERRY_PI_PTP_SETTINGS,
    ptp_priority_1=248,
    plugin_settings=PluginSettings(
        iperf_server=False, iperf_address="10.0.0.8", iperf_secondary_address="192.168.1.108",
        stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)
MACHINE_RPI07 = Machine(
    id="rpi07", address="rpi07", remote_root="/home/rpi/ptp-perf",
    **PTP_SLAVE_SETTINGS,
    endpoint_type=EndpointType.SECONDARY_SLAVE,
    **RASPBERRY_PI_PTP_SETTINGS,
    ptp_failover_master=True,
    ptp_priority_1=200,
    plugin_settings=PluginSettings(
        iperf_server=False, iperf_address="10.0.0.7", iperf_secondary_address="192.168.1.107",
        stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)
MACHINE_RPISERV = Machine(
    id="rpi-serv", address="rpi-serv", remote_root="/home/rpi/ptp-perf",
    endpoint_type=EndpointType.ORCHESTRATOR,
    ptp_interface="",
)

machines = {
    machine.id: machine for machine in [MACHINE_RPI06, MACHINE_RPI07, MACHINE_RPI08, MACHINE_RPISERV]
}

CLUSTER_PI = Cluster(
    id="rpi-4",
    name="Raspberry-Pi 4",
    machines=[
        MACHINE_RPI06, MACHINE_RPI08, MACHINE_RPI07
    ]
)
CLUSTER_RPI_SERV = Cluster(
    id="rpi-serv",
    name='RPI Server',
    machines=[
        MACHINE_RPISERV
    ]
)

clusters = {
    cluster.id: cluster for cluster in [CLUSTER_PI, CLUSTER_RPI_SERV]
}


@dataclass
class Configuration:
    cluster: Cluster = None
    machine: Optional[Machine] = None


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
    new_config.cluster = Cluster(
        id=configuration.cluster.id,
        name=configuration.cluster.name,
        machines=new_config.cluster.machines[0:num_machines],
    )
    return new_config
