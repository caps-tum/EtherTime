import asyncio
import logging
from typing import List, Dict, Tuple

from tinytuya import OutletDevice

from ptp_perf.adapters.adapter import Adapter
from ptp_perf.config import Configuration
from ptp_perf.machine import Machine
from ptp_perf.models import PTPEndpoint


class DeviceControl(Adapter):
    log_source = "fault-generator"

    # Which machine is plugged where
    machine_socket_map: Dict[str, Tuple[int, int]] = {
        'switch': (0, 1),
        'rpi06': (0, 2),
        'rpi07': (0, 4),
        'rpi08': (0, 6),
        'switch2': (1, 1),
        'rpi56': (1, 2),
        'rpi57': (1, 4),
        'rpi58': (1, 6),
    }

    power_strips: List[OutletDevice]
    configuration: Configuration

    def __init__(self, endpoint: PTPEndpoint, configuration: Configuration):
        super().__init__(endpoint)
        self.configuration = configuration

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
        machine = self.configuration.cluster.machine_by_type(self.endpoint.benchmark.fault_location)
        interval = self.endpoint.benchmark.fault_interval
        duration = self.endpoint.benchmark.fault_duration

        self.log(f"Scheduling hardware faults every {interval} on {machine}")

        if self.endpoint.benchmark.fault_ssh_keepalive:
            self.log(f"Turning SSH session keep-alive on")
            machine._ssh_session.keep_alive = True
        else:
            self.log(f"Not engaging SSH session keep-alive")

        try:
            while True:
                self.toggle_machine(machine, True)
                await asyncio.sleep(interval.total_seconds())
                # self.configuration.cluster.machine_by_id(machine)._ssh_session.keep_alive = True
                self.log(f"Scheduled hardware fault imminent on {machine}.")
                self.toggle_machine(machine, False)
                await asyncio.sleep(delay=duration.total_seconds())
                self.log(f"Scheduled hardware fault resolved on {machine}.")
                # self.configuration.cluster.machine_by_id(machine)._ssh_session.keep_alive = False
        finally:
            self.toggle_machine(machine, True)
