import copy
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from ptp_perf.machine import Cluster, Machine, PluginSettings
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.util import ImmediateException, str_join

RASPBERRY_PI_4_PTP_SETTINGS = {
    'ptp_interface': 'eth0',
    'ptp_use_phc2sys': False,
    'ptp_software_timestamping': True,
}
RASPBERRY_PI_5_PTP_SETTINGS = {
    'ptp_interface': 'eth0',
    'ptp_use_phc2sys': False,
    'ptp_software_timestamping': False,
}

PTP_SLAVE_SETTINGS = {
    'initial_clock_offset': timedelta(minutes=-1),
}

MACHINE_RPI06 = Machine(
    id="rpi06", address="rpi06", remote_root="/home/rpi/ptp-perf",
    ptp_address="10.0.0.6",
    endpoint_type=EndpointType.MASTER,
    **RASPBERRY_PI_4_PTP_SETTINGS,
    ptp_priority_1=1,
    plugin_settings=PluginSettings(
        iperf_server=True, iperf_address="10.0.0.6", iperf_secondary_address="192.168.1.106",
        stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)
MACHINE_RPI08 = Machine(
    id="rpi08", address="rpi08", remote_root="/home/rpi/ptp-perf",
    ptp_address="10.0.0.8",
    **PTP_SLAVE_SETTINGS,
    endpoint_type=EndpointType.PRIMARY_SLAVE,
    **RASPBERRY_PI_4_PTP_SETTINGS,
    ptp_priority_1=248,
    plugin_settings=PluginSettings(
        iperf_server=False, iperf_address="10.0.0.8", iperf_secondary_address="192.168.1.108",
        stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)
MACHINE_RPI07 = Machine(
    id="rpi07", address="rpi07", remote_root="/home/rpi/ptp-perf",
    ptp_address="10.0.0.7",
    **PTP_SLAVE_SETTINGS,
    endpoint_type=EndpointType.SECONDARY_SLAVE,
    **RASPBERRY_PI_4_PTP_SETTINGS,
    ptp_priority_1=200,
    plugin_settings=PluginSettings(
        iperf_server=False, iperf_address="10.0.0.7", iperf_secondary_address="192.168.1.107",
        stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)

MACHINE_RPI56 = Machine(
    id="rpi56", address="rpi56", remote_root="/home/rpi/ptp-perf",
    ptp_address="10.0.0.56",
    endpoint_type=EndpointType.MASTER,
    **RASPBERRY_PI_5_PTP_SETTINGS,
    ptp_priority_1=1,
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
    ptp_priority_1=248,
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
    ptp_priority_1=200,
    plugin_settings=PluginSettings(
        iperf_server=False, iperf_address="10.0.0.57", iperf_secondary_address="192.168.1.157",
        stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)

# New boards
PETALINUX_PTP_SETTINGS = {
    'ptp_interface': 'eth0',
    'ptp_use_phc2sys': False,
    'ptp_software_timestamping': False,
}

MACHINE_PETALINUX01 = Machine(
    id="petalinux01", address="petalinux01", remote_root="/home/rpi/ptp-perf",
    ptp_address="10.0.0.81",
    endpoint_type=EndpointType.MASTER,
    **PETALINUX_PTP_SETTINGS,
    ptp_priority_1=200,
    plugin_settings=PluginSettings(
        iperf_server=False, iperf_address="10.0.0.81", iperf_secondary_address="192.168.1.181",
        stress_ng_cpus=2, stress_ng_cpu_restrict_cores="1")
)
MACHINE_PETALINUX02 = Machine(
    id="petalinux02", address="petalinux02", remote_root="/home/rpi/ptp-perf",
    ptp_address="10.0.0.82",
    **PTP_SLAVE_SETTINGS,
    endpoint_type=EndpointType.PRIMARY_SLAVE,
    **PETALINUX_PTP_SETTINGS,
    ptp_priority_1=200,
    plugin_settings=PluginSettings(
        iperf_server=False, iperf_address="10.0.0.82", iperf_secondary_address="192.168.1.182",
        stress_ng_cpus=2, stress_ng_cpu_restrict_cores="1")
)
MACHINE_PETALINUX03 = Machine(
    id="petalinux03", address="petalinux03", remote_root="/home/rpi/ptp-perf",
    ptp_address="10.0.0.83",
    **PTP_SLAVE_SETTINGS,
    endpoint_type=EndpointType.PRIMARY_SLAVE,
    **PETALINUX_PTP_SETTINGS,
    ptp_priority_1=200,
    plugin_settings=PluginSettings(
        iperf_server=False, iperf_address="10.0.0.83", iperf_secondary_address="192.168.1.183",
        stress_ng_cpus=2, stress_ng_cpu_restrict_cores="1")
)
MACHINE_PETALINUX04 = Machine(
    id="petalinux04", address="petalinux04", remote_root="/home/rpi/ptp-perf",
    ptp_address="10.0.0.84",
    **PTP_SLAVE_SETTINGS,
    endpoint_type=EndpointType.PRIMARY_SLAVE,
    **PETALINUX_PTP_SETTINGS,
    ptp_priority_1=200,
    plugin_settings=PluginSettings(
        iperf_server=False, iperf_address="10.0.0.84", iperf_secondary_address="192.168.1.184",
        stress_ng_cpus=2, stress_ng_cpu_restrict_cores="1")
)


MACHINE_RPISERV = Machine(
    id="rpi-serv", address="rpi-serv", remote_root="/home/rpi/ptp-perf",
    ptp_address="0.0.0.0",
    endpoint_type=EndpointType.ORCHESTRATOR,
    ptp_interface="",
)

MACHINE_SWITCH = Machine(
    id="switch", endpoint_type=EndpointType.SWITCH,
    address=None, ptp_address=None, ptp_interface=None,
)
MACHINE_SWITCH2 = Machine(
    id="switch2", endpoint_type=EndpointType.SWITCH,
    address=None, ptp_address=None, ptp_interface=None,
)

machines = {
    machine.id: machine for machine in [
        MACHINE_RPI06, MACHINE_RPI07, MACHINE_RPI08,
        MACHINE_RPI56, MACHINE_RPI57, MACHINE_RPI58,
        MACHINE_RPISERV, MACHINE_SWITCH,
        MACHINE_SWITCH2,
        MACHINE_PETALINUX01, MACHINE_PETALINUX02, MACHINE_PETALINUX03, MACHINE_PETALINUX04,
    ]
}

CLUSTER_PI = Cluster(
    id="rpi-4",
    name="Raspberry-Pi 4",
    machines=[
        MACHINE_RPI06, MACHINE_RPI08, MACHINE_RPI07
    ]
)
CLUSTER_PI5 = Cluster(
    id="rpi-5",
    name="Raspberry-Pi 5",
    machines=[
        MACHINE_RPI56, MACHINE_RPI58, MACHINE_RPI57
    ]
)
CLUSTER_PETALINUX = Cluster(
    id="petalinux",
    name="Petalinux",
    machines=[
        MACHINE_PETALINUX01, MACHINE_PETALINUX02, MACHINE_PETALINUX03, MACHINE_PETALINUX04,
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
    cluster.id: cluster for cluster in [CLUSTER_PI, CLUSTER_PI5, CLUSTER_PETALINUX, CLUSTER_RPI_SERV]
}
ANALYZED_CLUSTERS = [CLUSTER_PI, CLUSTER_PI5, CLUSTER_PETALINUX]


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

