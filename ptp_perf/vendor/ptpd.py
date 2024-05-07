import io
import typing
from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from ptp_perf.invoke.invocation import Invocation
from ptp_perf.machine import MachineClientType
from ptp_perf.util import str_join
from ptp_perf.utilities import units
from ptp_perf.vendor.vendor import Vendor

if typing.TYPE_CHECKING:
    from ptp_perf.models import PTPEndpoint, LogRecord, Sample


@dataclass
class PTPDVendor(Vendor):
    id: str = "ptpd"
    name: str = "PTPd"
    supports_non_standard_config_interval: bool = True
    _process: Invocation = None

    def running(self):
        if self._process is not None:
            return self._process.running
        return False

    @property
    def installed(self):
        return self.check_executable_present("ptpd")

    def install(self):
        self.invoke_package_manager("ptpd")

    def uninstall(self):
        self.invoke_package_manager("ptpd", action="purge")

    async def run(self, endpoint: "PTPEndpoint"):

        effective_client_type = endpoint.get_effective_client_type()
        self._process = Invocation.of_command(
            # Run PTPd through stdbuf line buffering so that we get log lines as they are emitted.
            "stdbuf", "-eL", "-oL",
            "ptpd",
            "-i", endpoint.machine.ptp_interface,
            "--verbose",
        ).append_arg_if_present(
            # We don't supply this on failover
            '--masteronly', effective_client_type.is_primary_master()
        ).append_arg_if_present(
            '--slaveonly', effective_client_type == MachineClientType.SLAVE
        ).as_privileged()
        self._process.keep_alive = endpoint.benchmark.ptp_keepalive

        await self._process.run()

    async def restart(self, kill: bool = True, restart_delay: timedelta = timedelta(seconds=1)):
        await self._process.restart(kill, ignore_return_code=True, restart_delay=restart_delay)


    @classmethod
    def parse_log_data(cls, endpoint: "PTPEndpoint") -> typing.List["Sample"]:
        from ptp_perf.models.sample import Sample

        # Since we use stdbuf for ptpd now we also need to use that as a source.
        logs: typing.List[LogRecord] = endpoint.logrecord_set.filter(source="stdbuf").all()

        # Keep only the CSV header and the statistics lines in the state "slave"
        # We are only interested in the first CSV header (when process is restarted there might be multiple)
        csv_header_lines = [log for log in logs if log.message.lstrip("| ").startswith("# Timestamp")]

        if len(csv_header_lines) == 0:
            # Probably master node or other node without data.
            return []

        # We insert the database timestamps into the CSV string so we can extract it later.
        filtered_log = csv_header_lines[0].message.lstrip("| ").rstrip("\n") + ", DB Timestamp\n"
        # Actual data.
        filtered_log += str_join(
            [log.message.lstrip("| ") + f", {log.timestamp}" for log in logs if ", slv, " in log.message],
            separator='\n'
        )

        frame = pd.read_csv(
            io.StringIO(filtered_log), delimiter=",", skipinitialspace=True, parse_dates=True
        )

        # | # Timestamp, State, Clock ID, One Way Delay, Offset From Master, Slave to Master, Master to Slave, Observed Drift, Last packet Received, One Way Delay Mean, One Way Delay Std Dev, Offset From Master Mean, Offset From Master Std Dev, Observed Drift Mean, Observed Drift Std Dev, raw delayMS, raw delaySM
        # | 2024-03-06 19:32:49.655021, slv, dca632fffecdcf52(unknown)/1,  0.000062474, -0.000028681,  0.000092819,  0.000028279, -6677.771000000, D, 0.000061376, 221, -0.000044591, 10390, -5282, 392,  0.000028279,  0.000092819

        samples = []
        for index, row in frame.iterrows():
            samples.append(
                Sample(
                    endpoint=endpoint,
                    timestamp=row["DB Timestamp"],
                    sample_type=Sample.SampleType.CLOCK_DIFF,
                    value=row["Offset From Master"] * units.NANOSECONDS_IN_SECOND,
                )
            )
            samples.append(
                Sample(
                    endpoint=endpoint,
                    timestamp=row["DB Timestamp"],
                    sample_type=Sample.SampleType.PATH_DELAY,
                    value=row["One Way Delay"] * units.NANOSECONDS_IN_SECOND,
                )
            )

        Sample.objects.bulk_create(samples)
        return samples

    def get_processes(self) -> typing.Iterable[Invocation]:
        return (self._process,)
