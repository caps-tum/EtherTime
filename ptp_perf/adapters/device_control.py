import asyncio
import logging
from typing import List, Dict, Tuple

from tinytuya import OutletDevice

from ptp_perf.adapters.adapter import Adapter
from ptp_perf.config import Configuration
from ptp_perf.machine import Machine
from ptp_perf.models import PTPEndpoint
from ptp_perf.util import str_join


class DeviceControl(Adapter):
    """
    Adapter to control power outlets on a power strip, used to simulate hardware faults.
    We use Tuya smart PDUs to control power delivery to machines and network switches.
    """
    log_source = "fault-generator"

    # Which machine is plugged where
    # Each machine is assigned to a power strip and a port on that power strip
    # Power strips are defined below.
    machine_socket_map: Dict[str, Tuple[int, int]] = {
        'switch': (0, 1),
        'rpi06': (0, 2),
        'rpi07': (0, 4),
        'rpi08': (0, 6),
        'switch2': (1, 1),
        'rpi56': (1, 2),
        'rpi57': (1, 4),
        'rpi58': (1, 6),
        'petalinux01': (2, 1),
        'petalinux02': (2, 2),
        'petalinux03': (2, 4),
        'petalinux04': (2, 6),
    }

    # Configuration for the power strips
    # See below for defining your own power strips
    power_strips: List[OutletDevice]
    configuration: Configuration

    def __init__(self, endpoint: PTPEndpoint, configuration: Configuration):
        super().__init__(endpoint)
        self.configuration = configuration

        # Each power strip is defined by its IP address, local key, and version.
        # Refer to the Tuya API documentation and tinytuya for more information.
        # Determining the local key is a bit tricky, but by using the Tuya Cloud API.
        # Lookup online tutorials on how to extract the local key from the Tuya Cloud API.
        self.power_strips = [
            OutletDevice(
                dev_id="eb06b72cf6479cd3bdcuzi",
                address="192.168.1.200",
                local_key="3mqG5q4$4Nd<!?:`",
                version=3.3,
            ),
            OutletDevice(
                dev_id="eb44349e87ad1b54086akt",
                address="192.168.1.201",
                local_key="H.BBK_VnvCu}O53%",
                version=3.4,
            ),
            OutletDevice(
                dev_id="eb40abdcfe68048f2a7jcn",
                address="192.168.1.202",
                local_key="PlX?5Zk~tU@a`<`&",
                version=3.4,
            )
        ]

    def toggle_machine(self, machine: Machine, state: bool):
        """
        Toggle the power state of a machine by sending a control message to the power strip.
        :param machine: The machine to control.
        :param state: Whether to turn the machine on or off.
        :return:
        """
        try:
            power_strip_id, port = self.machine_socket_map[machine.id]
        except KeyError:
            raise RuntimeError(f"Machine {machine} is not assigned to a power strip socket.")

        logging.debug(f"Sending device control message to power strip port {port}@{power_strip_id}: {state}")
        result_data = self.power_strips[power_strip_id].set_status(state, switch=port)

        # Sample response (run this code with debug logging)
        # set_status received data={'protocol': 4, 't': 1714081639, 'data': {'dps': {'6': True}, 'type': 'query'}, 'dps': {'6': True}}
        new_port_state = result_data['dps'][str(port)]
        logging.debug(f"Tuya Result: {new_port_state}")
        if state != new_port_state:
            raise RuntimeError(f"Failed to actuate the power strip (new state {new_port_state} != target {state}, response data: {result_data})")


    async def run(self):
        """
        Run the hardware fault generator as a background task.
        Each fault is scheduled at a fixed interval and lasts for a fixed duration, where the machine is turned off.
        The location of the fault is determined by the benchmark configuration and the cluster configuration.
        :return:
        """
        machines = self.configuration.cluster.machines_by_type(self.endpoint.benchmark.fault_location)
        if len(machines) == 0:
            raise RuntimeError(
                f"Could not find machines in cluster to create faults on: {self.endpoint.benchmark.fault_location}"
            )

        interval = self.endpoint.benchmark.fault_interval
        duration = self.endpoint.benchmark.fault_duration

        self.log(f"Scheduling hardware faults every {interval} on {str_join(machines)}")

        if self.endpoint.benchmark.fault_ssh_keepalive:
            self.log(f"Turning SSH session keep-alive on")
            for machine in machines:
                machine._ssh_session.keep_alive = True
        else:
            self.log(f"Not engaging SSH session keep-alive")

        try:
            while True:
                # Ensure that machines are always turned on at the beginning of the run
                for machine in machines:
                    self.toggle_machine(machine, True)

                # Wait for the first fault
                await asyncio.sleep(interval.total_seconds())

                # Create first fault
                # self.configuration.cluster.machine_by_id(machine)._ssh_session.keep_alive = True
                for machine in machines:
                    self.log(f"Scheduled hardware fault imminent on {machine}.")
                    self.toggle_machine(machine, False)

                # Fault duration
                await asyncio.sleep(delay=duration.total_seconds())

                # Print resolved, machines will be turned back on in next iteration.
                for machine in machines:
                    self.log(f"Scheduled hardware fault resolved on {machine}.")
                # self.configuration.cluster.machine_by_id(machine)._ssh_session.keep_alive = False
        finally:
            self.toggle_machine(machine, True)
