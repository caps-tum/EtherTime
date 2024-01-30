import shutil
import typing
from dataclasses import dataclass

from invoke.invocation import Invocation

if typing.TYPE_CHECKING:
    from profiles.base_profile import BaseProfile
    from profiles.timeseries_profile import TimeseriesProfile


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

    async def start(self):
        raise NotImplementedError()


    async def stop(self):
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

    def convert_profile(self, profile: "BaseProfile") -> "TimeseriesProfile":
        raise NotImplementedError(f"Cannot convert the profile for vendor {self.name}")
