import re
import typing
from dataclasses import dataclass
from datetime import timedelta

from config import current_configuration
from invoke.invocation import Invocation
from utilities import units
from vendor.vendor import Vendor

if typing.TYPE_CHECKING:
    from profiles.base_profile import BaseProfile, ProfileType


@dataclass
class LinuxPTPVendor(Vendor):
    id: str = "linuxptp"
    name: str = "LinuxPTP"

    _process_ptp4l: Invocation = None
    _process_phc2sys: Invocation = None

    @property
    def installed(self):
        return self.check_executable_present("ptp4l")

    # @property
    # def running(self):
    #     pass

    async def start(self):
        machine = current_configuration.machine

        self._process_ptp4l = await Invocation.of_command(
            "ptp4l", "-i", machine.ptp_interface, "-m"
        ).append_arg_if_present(
            "-s", condition=not machine.ptp_master,
        ).append_arg_if_present(
            "-S", condition=machine.ptp_software_timestamping
        ).as_privileged().start_async()
        self._process_ptp4l.communicate_in_background()

        if machine.ptp_use_phc2sys:
            self._process_phc2sys = await Invocation.of_command(
                "phc2sys", "-m", "-a", "-r",
            ).append_arg_if_present(
                # We append -r a *second* time on master.
                # This allows not only phc --> sys but also sys --> phc, which we want on the master.
                "-r", condition=machine.ptp_master,
            ).as_privileged().start_async()
            self._process_phc2sys.communicate_in_background()


    async def stop(self):
        if self._process_ptp4l is not None:
            await self._process_ptp4l.terminate()
        if self._process_phc2sys is not None:
            await self._process_phc2sys.terminate()

    def collect_data(self, profile: "BaseProfile"):
        profile.raw_data = {
            'ptp4l_log': self._process_ptp4l.output if self._process_ptp4l is not None else None,
            'phc2sys_log': self._process_phc2sys.output if self._process_phc2sys is not None else None,
        }

    @property
    def install_supported(self):
        return super().install_supported

    def install(self):
        self.invoke_package_manager("linuxptp")

    def uninstall(self):
        self.invoke_package_manager("linuxptp", action="purge")

    def convert_profile(self, profile: "BaseProfile"):
        import pandas as pd
        from profiles.base_profile import BaseProfile, ProfileType

        if profile.raw_data["phc2sys_log"] is not None:
            raise NotImplementedError("Cannot import phc2sys log for the moment.")

        log = profile.raw_data["ptp4l_log"]

        timestamps = []
        offsets = []
        for match in re.finditer(
            pattern="ptp4l\[(?P<timestamp>[0-9.+-]+)\]: master offset \s*(?P<master_offset>[0-9.+-]+)\s* s\d+ freq \s*(?P<s0_freq>[0-9.+-]+)\s* path delay\s* (?P<path_delay>[0-9.+-]+)",
            string=log,
        ):
            timestamps.append(timedelta(seconds=float(match.group("timestamp"))))
            offsets.append(int(match.group("master_offset")) * units.NANOSECONDS_TO_SECONDS)

        if len(timestamps) == 0:
            return None

        return BaseProfile.template_from_existing(profile, ProfileType.PROCESSED).set_timeseries_data(
            pd.Series(timestamps), pd.Series(offsets)
        )
