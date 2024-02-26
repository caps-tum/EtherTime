from tinytuya import OutletDevice

from machine import Machine


class DeviceControl:
    id = "ebb88e5f6700fa300acvqr"
    ip = "192.168.1.200"
    key = "Ow/wW6UPpqT2%N5u"

    # Which machine is plugged where
    machine_socket_map = {
        'switch': 0,
        'rpi06': 2,
        'rpi07': 4,
        'rpi08': 6,
    }

    power_strip: OutletDevice

    def __init__(self):
        self.power_strip = OutletDevice(
            dev_id=self.id,
            address=self.ip,
            local_key=self.key,
            version=3.3,
        )

    def toggle_machine(self, machine: Machine, state: bool):
        try:
            port = self.machine_socket_map[machine.id]
            self.power_strip.set_status(state, switch=port)
        except KeyError:
            raise RuntimeError(f"Machine {machine.id} is not assigned to a power strip socket.")
