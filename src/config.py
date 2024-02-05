from datetime import timedelta

import util
from machine import Cluster, Machine, PluginSettings

RASPBERRY_PI_PTP_SETTINGS = {
    'ptp_interface': 'eth0',
    'ptp_use_phc2sys': False,
    'ptp_software_timestamping': True,
}

configs = {
    "Pi Cluster": Cluster(
        machines=[
            Machine(
                id="rpi06",
                address="rpi06",
                remote_root="/home/rpi/ptp-perf",
                ptp_master=True,
                **RASPBERRY_PI_PTP_SETTINGS,
                plugin_settings=PluginSettings(
                    iperf_server=True,
                    iperf_address="10.0.0.6",
                    stress_ng_cpus=4,
                )
            ),
            Machine(
                id="rpi08",
                address="rpi08",
                remote_root="/home/rpi/ptp-perf",
                ptp_master=False,
                initial_clock_offset=timedelta(minutes=-1),
                **RASPBERRY_PI_PTP_SETTINGS,
                plugin_settings=PluginSettings(
                    iperf_server=False,
                    iperf_address="10.0.0.8",
                    stress_ng_cpus=4,
                )
            )
        ]
    )
}

class Configuration:
    cluster: Cluster = None
    machine: Machine = None

current_configuration = Configuration()

# Currently we default to the first (only) defined cluster
current_configuration.cluster = configs["Pi Cluster"]

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
