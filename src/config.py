from datetime import timedelta

import util
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
    plugin_settings=PluginSettings(iperf_server=False, iperf_address=None, stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)
MACHINE_RPISERV = Machine(
    id="rpi-serv", address="rpi-serv", remote_root="/home/rpi/ptp-perf",
    ptp_interface="",
)


clusters = {
    "Pi Cluster": Cluster(
        machines=[
            MACHINE_RPI06, MACHINE_RPI08
        ]
    ),
    "rpi-serv": Cluster(
        machines=[
            MACHINE_RPISERV
        ]
    ),
    "3-Pi": Cluster(
        machines=[MACHINE_RPI06, MACHINE_RPI08, MACHINE_RPI07],
    )
}


class Configuration:
    cluster: Cluster = None
    machine: Machine = None


current_configuration = Configuration()

# Currently we default to the first (only) defined cluster
current_configuration.cluster = clusters["Pi Cluster"]
# current_configuration.cluster = clusters["3-Pi"]


def verify(configuration: Configuration):
    """Verify that the configuration is valid."""

    # Check unique ids
    ids = [machine.id for machine in configuration.cluster.machines]
    if len(set(ids)) != len(ids):
        raise RuntimeError("The configuration contains duplicate machine ids.")


verify(current_configuration)


def set_machine(id: str):
    current_configuration.machine = util.unpack_one_value_or_error(
        [machine for machine in current_configuration.cluster.machines if machine.id == id],
        message=f"No or too many machines found for machine id {id}.",
    )

def set_machine_direct(machine: Machine):
    current_configuration.machine = machine

def get_configuration_by_cluster_name(name: str) -> Configuration:
    try:
        cluster = clusters[name]
    except KeyError:
        raise ImmediateException(f"Configuration not found: {name} (from {str_join(clusters.keys())})")

    configuration = Configuration()
    configuration.cluster = cluster

    verify(configuration)
    return configuration
