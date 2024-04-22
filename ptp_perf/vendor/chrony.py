import asyncio
import math
import typing
from asyncio import Task, TaskGroup
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from ptp_perf.invoke.invocation import Invocation
from ptp_perf.machine import MachineClientType
from ptp_perf.utilities import units
from ptp_perf.vendor.vendor import Vendor

if typing.TYPE_CHECKING:
    from ptp_perf.models import PTPEndpoint, Sample


@dataclass
class ChronyVendor(Vendor):
    id: str = "chrony"
    name: str = "Chrony"
    _process: Invocation = None
    _process_readlog: Invocation = None

    CHRONY_MEASUREMENTS_LOG_FILE = "/tmp/log/chrony/measurements.log"

    def running(self):
        if self._process is not None:
            return self._process.running
        return False

    @property
    def installed(self):
        return self.check_executable_present("/usr/sbin/chronyd")

    def install(self):
        raise NotImplementedError()

    def uninstall(self):
        raise NotImplementedError()

    async def run(self, endpoint: "PTPEndpoint"):

        self._process = Invocation.of_command(
            "chronyd",
            "-d",
            "-f", str(self.config_file_path),
        ).as_privileged()
        # Read measurements.log as it is being written.
        measurements_file = Path(self.CHRONY_MEASUREMENTS_LOG_FILE)
        measurements_file.unlink(missing_ok=True)
        measurements_file.parent.mkdir(parents=True, exist_ok=True)
        # Setting mode directly on touch does not work, as it is combined with the umask.
        measurements_file.touch()
        measurements_file.chmod(mode=0o666)

        self._process_readlog = Invocation.of_command(
            "stdbuf", "-eL", "-oL", "tail", "-f", '--bytes=+0', str(measurements_file)
        )
        # Ignore the readlog process getting cancelled.
        self._process_readlog.expected_return_codes.append(-15)

        self._process.keep_alive = endpoint.benchmark.ptp_keepalive

        async with TaskGroup() as task_group:
            task_group.create_task(self._process.run(), name="Chronyd")
            await asyncio.sleep(1)
            task_group.create_task(self._process_readlog.run(), name="Chronyd Logs")


    @staticmethod
    async def initial_time_synchronization():
        try:
            await Invocation.of_command("service", "chrony", "start").as_privileged().run()

            # Wait for offset <1.0
            await Invocation.of_command("chronyc", "waitsync", "10", "1.0").run()
        finally:
            await Invocation.of_command("service", "chrony", "stop").as_privileged().run()

    async def restart(self, kill: bool = True, restart_delay: timedelta = timedelta(seconds=1)):
        await self._process.restart(kill, ignore_return_code=True, restart_delay=restart_delay)

    def config_file_source_path(self, base_path: Path, endpoint: "PTPEndpoint") -> Path:
        effective_client_type = endpoint.get_effective_client_type()
        return {
            MachineClientType.MASTER: base_path.joinpath("chrony_template_master.conf"),
            MachineClientType.FAILOVER_MASTER: base_path.joinpath("chrony_template_failover_master.conf"),
            MachineClientType.SLAVE: base_path.joinpath("chrony_template_slave.conf"),
        }[effective_client_type]

    @classmethod
    def parse_log_data(cls, endpoint: "PTPEndpoint") -> typing.List["Sample"]:
        # Regex shorthand for number in scientific notation
        scientific_number = '[+-]?\d+\.\d+e[+-]\d+'
        return Vendor.extract_sample_from_log_using_regex(
            endpoint,
            source_name='stdbuf',
            # Log line:
            # 2024-04-10 20:43:50 10.0.0.56       N 10 111 111 1111   0  0 1.00 -4.530e-07  1.526e-04  1.146e-07  0.000e+00  0.000e+00 7F7F0101 4I K K
            # Regex: Date + Time + IP at beginning of address. Then stuff in between, then offset, peer delay, peer displacement, root delay and root displacement all as scientific notation
            # Literal pattern: \d+-\d+-\d+ \d+:\d+:\d+ \d+\.\d+\.\d+\.\d+ .* (?P<master_offset>[+-]?\d+\.\d+e[+-]\d+)\s*(?P<path_delay>[+-]?\d+\.\d+e[+-]\d+)\s*[+-]?\d+\.\d+e[+-]\d+\s+[+-]?\d+\.\d+e[+-]\d+\s+[+-]?\d+\.\d+e[+-]\d+\s+
            pattern='\d+-\d+-\d+ \d+:\d+:\d+ \d+\.\d+\.\d+\.\d+ .* (?P<master_offset>' + scientific_number + ')\s*(?P<path_delay>' + scientific_number + ')\s*' + scientific_number + '\s+' + scientific_number + '\s+' + scientific_number + '\s+',
            number_conversion=lambda x: int(float(x) * units.NANOSECONDS_IN_SECOND)
        )
