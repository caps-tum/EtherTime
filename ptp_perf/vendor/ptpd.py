import io
import logging
import typing
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from ptp_perf.invoke.invocation import Invocation
from ptp_perf.profiles.base_profile import BaseProfile, ProfileType
from ptp_perf.util import str_join
from ptp_perf.vendor.vendor import Vendor

if typing.TYPE_CHECKING:
    from ptp_perf.models import PTPEndpoint


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
        self._process.restart_delay = endpoint.benchmark.ptp_restart_delay

        await self._process.run()

    async def restart(self, kill: bool = True):
        await self._process.restart(kill, ignore_return_code=True)

    def collect_data(self, profile: "BaseProfile"):
        profile.raw_data.update(
            log=self._process.output if self._process is not None else None,
        )

    @classmethod
    def convert_profile(cls, raw_profile: "BaseProfile") -> Optional[BaseProfile]:
        # In old profiles, statistics were in statistics while the regular log was in "log".
        # New profiles merge all data into log.
        log = raw_profile.raw_data["statistics"] if "statistics" in raw_profile.raw_data.keys() else raw_profile.raw_data["log"]

        if log is None:
            logging.warning("Profile without ptpd log, corrupted.")

        # Keep only the CSV header and the statistics lines in the state "slave"
        # We are only interested in the first CSV header (when process is restarted there might be multiple)
        csv_header_lines = [line for line in log.splitlines(keepends=True) if line.startswith("# Timestamp")]
        filtered_log = csv_header_lines[0]
        # Actual data.
        filtered_log += str_join(
            [line for line in log.splitlines(keepends=True) if ", slv, " in line],
            separator=''
        )

        frame = pd.read_csv(
            io.StringIO(filtered_log), delimiter=",", skipinitialspace=True, parse_dates=True
        )
        # No longer necessary, the filtering is done above.
        # frame = frame[frame["State"] == "slv"]

        if frame.empty:
            return None

        timestamps = pd.to_datetime(frame["# Timestamp"])
        clock_offsets = frame["Offset From Master"]
        path_delays = frame["One Way Delay"]

        return BaseProfile.template_from_existing(raw_profile, ProfileType.PROCESSED).process_timeseries_data(
            timestamps, clock_offsets, path_delays, #resample=timedelta(seconds=1)
            # Resampling doesn't work well with bootstrapping, it produces intermittent NaN values when there is a gap.
        )
