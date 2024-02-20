import shutil
import typing
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from constants import LOCAL_DIR, PTPPERF_REPOSITORY_ROOT
from invoke.invocation import Invocation

if typing.TYPE_CHECKING:
    from profiles.base_profile import BaseProfile


@dataclass
class Vendor:
    id: str
    name: str

    @property
    def installed(self):
        """Whether this vendor is installed"""
        raise NotImplementedError()

    @property
    def running(self):
        raise NotImplementedError()

    async def run(self):
        raise NotImplementedError()

    async def restart(self, kill: bool = True):
        raise NotImplementedError()


    @property
    def install_supported(self):
        return False

    def install(self):
        raise NotImplementedError()

    def uninstall(self):
        raise NotImplementedError()

    def __eq__(self, other):
        return self.id == other.id

    def __str__(self):
        return self.name

    def collect_data(self, profile: "BaseProfile"):
        raise NotImplementedError()

    # These don't really belong here but for now it's ok

    @staticmethod
    def invoke_package_manager(package, action="install"):
        return Invocation.of_command("apt-get", action, "-y", package).as_privileged().run()

    @staticmethod
    def check_executable_present(executable) -> bool:
        return shutil.which(executable) is not None

    def convert_profile(self, profile: "BaseProfile") -> Optional["BaseProfile"]:
        raise NotImplementedError(f"Cannot convert the profile for vendor {self.name}")


    @property
    def config_file_path(self) -> Path:
        return LOCAL_DIR.joinpath("ptp-config.txt")


    def create_configuration_file(self, profile: "BaseProfile") -> Path:
        # Render the configuration template file to a temporary file and return it
        template = PTPPERF_REPOSITORY_ROOT.joinpath("deploy").joinpath("config").joinpath(f"{self.id}_template.conf").read_text()
        output = template.format(ptp_config=profile.benchmark.ptp_config)
        output_file = self.config_file_path
        output_file.write_text(output)
        return output_file
