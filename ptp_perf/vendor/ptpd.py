import io
import typing
from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from ptp_perf.invoke.invocation import Invocation
from ptp_perf.util import str_join
from ptp_perf.vendor.vendor import Vendor

if typing.TYPE_CHECKING:
    from ptp_perf.models import PTPEndpoint, LogRecord, Sample


@dataclass
class PTPDVendor(Vendor):
    id: str = "ptpd"
    name: str = "PTPd"
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

        self._process = Invocation.of_command(
            "ptpd", "-i", endpoint.machine.ptp_interface, "--verbose",
            '--masteronly' if endpoint.machine.ptp_master else '--slaveonly',
            "--config-file", str(self.config_file_path),
        ).as_privileged()
        self._process.keep_alive = endpoint.benchmark.ptp_keepalive

        await self._process.run()

    async def restart(self, kill: bool = True, restart_delay: timedelta = timedelta(seconds=1)):
        await self._process.restart(kill, ignore_return_code=True, restart_delay=restart_delay)


    @classmethod
    def parse_log_data(cls, endpoint: "PTPEndpoint") -> typing.List["Sample"]:
        from ptp_perf.models.sample import Sample

        logs: typing.List[LogRecord] = endpoint.logrecord_set.filter(source="ptpd").all()

        # Keep only the CSV header and the statistics lines in the state "slave"
        # We are only interested in the first CSV header (when process is restarted there might be multiple)
        csv_header_lines = [log for log in logs if log.message.lstrip("| ").startswith("# Timestamp")]

        if len(csv_header_lines) == 0:
            # Probably master node or other node without data.
            return []

        filtered_log = csv_header_lines[0].message.lstrip("| ")
        timezone = csv_header_lines[0].timestamp.tzinfo
        # Actual data.
        filtered_log += str_join(
            [log.message.lstrip("| ") for log in logs if ", slv, " in log.message],
            separator='\n'
        )

        frame = pd.read_csv(
            io.StringIO(filtered_log), delimiter=",", skipinitialspace=True, parse_dates=True
        )
        frame["# Timestamp"] = frame["# Timestamp"].astype('datetime64[ns]').dt.tz_localize(timezone)
        # No longer necessary, the filtering is done above.
        # frame = frame[frame["State"] == "slv"]

        # | # Timestamp, State, Clock ID, One Way Delay, Offset From Master, Slave to Master, Master to Slave, Observed Drift, Last packet Received, One Way Delay Mean, One Way Delay Std Dev, Offset From Master Mean, Offset From Master Std Dev, Observed Drift Mean, Observed Drift Std Dev, raw delayMS, raw delaySM
        # | 2024-03-06 19:32:49.655021, slv, dca632fffecdcf52(unknown)/1,  0.000062474, -0.000028681,  0.000092819,  0.000028279, -6677.771000000, D, 0.000061376, 221, -0.000044591, 10390, -5282, 392,  0.000028279,  0.000092819

        samples = []
        for index, row in frame.iterrows():
            samples.append(
                Sample(
                    endpoint=endpoint,
                    timestamp=row["# Timestamp"],
                    sample_type=Sample.SampleType.CLOCK_DIFF,
                    value=row["Offset From Master"],
                )
            )
            samples.append(
                Sample(
                    endpoint=endpoint,
                    timestamp=row["# Timestamp"],
                    sample_type=Sample.SampleType.PATH_DELAY,
                    value=row["One Way Delay"],
                )
            )

        Sample.objects.bulk_create(samples)
        return samples
