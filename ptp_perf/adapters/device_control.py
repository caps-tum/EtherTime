import asyncio

from tinytuya import OutletDevice

from ptp_perf.adapters.adapter import Adapter
from ptp_perf.profiles.base_profile import BaseProfile


class DeviceControl(Adapter):
    id = "ebb88e5f6700fa300acvqr"
    ip = "192.168.1.200"
    key = "Ow/wW6UPpqT2%N5u"

    # Which machine is plugged where
    machine_socket_map = {
        'switch': 1,
        'rpi06': 2,
        'rpi07': 4,
        'rpi08': 6,
    }

    power_strip: OutletDevice

    def __init__(self, profile: BaseProfile):
        super().__init__(profile)
        self.power_strip = OutletDevice(
            dev_id=self.id,
            address=self.ip,
            local_key=self.key,
            version=3.3,
        )

    def toggle_machine(self, machine_id: str, state: bool):
        try:
            port = self.machine_socket_map[machine_id]
            self.power_strip.set_status(state, switch=port)
        except KeyError:
            raise RuntimeError(f"Machine {machine_id} is not assigned to a power strip socket.")


    async def run(self):
        machine_id = self.profile.benchmark.fault_tolerance_hardware_fault_machine
        interval = self.profile.benchmark.fault_tolerance_hardware_fault_interval

        self.log(f"Scheduling hardware faults every {interval} on {machine_id}")
        try:
            while True:
                self.toggle_machine(machine_id, True)
                await asyncio.sleep(interval.total_seconds())
                self.log(f"Scheduled hardware fault imminent on {machine_id}.")
                self.toggle_machine(machine_id, False)
                await asyncio.sleep(delay=5)
                self.log(f"Scheduled hardware fault resolved on {machine_id}.")
        finally:
            self.toggle_machine(machine_id, True)
