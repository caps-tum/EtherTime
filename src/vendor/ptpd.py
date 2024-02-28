import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

import constants
from invoke.invocation import Invocation
from profiles.base_profile import BaseProfile, ProfileType
from util import str_join
from vendor.vendor import Vendor


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

    async def run(self, profile: "BaseProfile"):

        # Create output path
        Path(constants.MEASUREMENTS_DIR).mkdir(exist_ok=True)
        # Remove previous logs
        Path(self.log_file_path).unlink(missing_ok=True)
        Path(self.statistics_file_path).unlink(missing_ok=True)

        self._process = Invocation.of_command(
            "ptpd", "-i", profile.configuration.machine.ptp_interface, "--verbose",
            '--masteronly' if profile.configuration.machine.ptp_master else '--slaveonly',
            "--config-file", str(self.config_file_path),
        ).as_privileged()
        self._process.keep_alive = profile.benchmark.ptp_keepalive

        await self._process.run()


    @property
    def statistics_file_path(self):
        return constants.LOCAL_DIR.joinpath("ptpd-statistics.txt")

    @property
    def log_file_path(self):
        return constants.LOCAL_DIR.joinpath("ptpd-log.txt")

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
