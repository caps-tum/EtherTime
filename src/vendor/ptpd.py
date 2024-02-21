import io
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

import constants
from config import current_configuration
from invoke.invocation import Invocation
from profiles.base_profile import BaseProfile, ProfileType
from util import read_file_if_exists
from vendor.vendor import Vendor


@dataclass
class PTPDVendor(Vendor):
    id: str = "ptpd"
    name: str = "PTPd"
    _process: Invocation = None


    def running(self):
        """Check whether a PTPd instance is running by resolving the PTPd lock file. """

        # This command prints the path to the log file
        ptpd_determine_path = Invocation.of_command(
            "ptpd", *self.ptpd_interface_options, "-p"
        ).as_privileged().hide_unless_failure().run_sync()

        # We check whether the file exists.
        return Path(ptpd_determine_path.output).exists()

    @property
    def installed(self):
        return self.check_executable_present("ptpd")

    def install(self):
        self.invoke_package_manager("ptpd")

    def uninstall(self):
        self.invoke_package_manager("ptpd", action="purge")

    async def run(self):

        # Create output path
        Path(constants.MEASUREMENTS_DIR).mkdir(exist_ok=True)
        # Remove previous logs
        Path(self.log_file_path).unlink(missing_ok=True)
        Path(self.statistics_file_path).unlink(missing_ok=True)

        self._process = Invocation.of_command(
            "ptpd", *self.ptpd_interface_options, "--foreground",
            '--masteronly' if current_configuration.machine.ptp_master else '--slaveonly',
            '--log-file', str(self.log_file_path),
            "--statistics-file", str(self.statistics_file_path),
            "--config-file", str(self.config_file_path),
        ).as_privileged()

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
            log=read_file_if_exists(self.log_file_path),
            statistics= read_file_if_exists(self.statistics_file_path),
        )

    @property
    def ptpd_interface_options(self):
        return ["-i", current_configuration.machine.ptp_interface]


    @classmethod
    def convert_profile(cls, raw_profile: "BaseProfile") -> Optional[BaseProfile]:
        frame = pd.read_csv(
            io.StringIO(raw_profile.raw_data["statistics"]), delimiter=",", skipinitialspace=True,
            parse_dates=True
        )
        frame = frame[frame["State"] == "slv"]

        if frame.empty:
            return None

        timestamps = pd.to_datetime(frame["# Timestamp"])
        clock_offsets = frame["Offset From Master"]
        path_delays = frame["One Way Delay"]

        return BaseProfile.template_from_existing(raw_profile, ProfileType.PROCESSED).process_timeseries_data(
            timestamps, clock_offsets, path_delays, #resample=timedelta(seconds=1)
            # Resampling doesn't work well with bootstrapping, it produces intermittent NaN values when there is a gap.
        )
