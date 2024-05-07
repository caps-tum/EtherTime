import re
import shutil
import typing
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from ptp_perf.constants import LOCAL_DIR, PTPPERF_REPOSITORY_ROOT
from ptp_perf.invoke.invocation import Invocation

if typing.TYPE_CHECKING:
    from ptp_perf.models import PTPEndpoint, Sample, LogRecord


@dataclass
class Vendor:
    id: str
    name: str
    supports_non_standard_config_interval: bool = False

    @property
    def installed(self):
        """Whether this vendor is installed"""
        raise NotImplementedError()

    @property
    def running(self):
        raise NotImplementedError()

    async def run(self, endpoint: "PTPEndpoint"):
        raise NotImplementedError()

    async def restart(self, kill: bool = True, restart_delay: timedelta = timedelta(seconds=1)):
        raise NotImplementedError()


    @property
    def install_supported(self):
        return False

    def install(self):
        raise NotImplementedError()

    def uninstall(self):
        raise NotImplementedError()

    def get_processes(self) -> typing.Iterable[Invocation]:
        raise NotImplementedError()

    def __eq__(self, other):
        return self.id == other.id

    def __str__(self):
        return self.name

    # These don't really belong here but for now it's ok

    @staticmethod
    def invoke_package_manager(package, action="install"):
        return Invocation.of_command("apt-get", action, "-y", package).as_privileged().run()

    @staticmethod
    def check_executable_present(executable) -> bool:
        return shutil.which(executable) is not None

    def parse_log_data(self, endpoint: "PTPEndpoint") -> typing.List["Sample"]:
        raise NotImplementedError(f"Cannot parse log data for vendor {self.name}")


    @property
    def config_file_path(self) -> Path:
        return LOCAL_DIR.joinpath("ptp-config.txt")


    def config_file_source_path(self, base_path: Path, endpoint: "PTPEndpoint") -> Path:
        return base_path.joinpath(f"{self.id}_template.conf")


    def create_configuration_file(self, endpoint: "PTPEndpoint") -> Path:
        # Render the configuration template file to a temporary file and return it

        if not self.supports_non_standard_config_interval and endpoint.benchmark.ptp_config.has_non_standard_intervals:
            raise NotImplementedError(f"Vendor {self} does not support non standard PTP configuration intervals")

        template_source_path = self.config_file_source_path(
            PTPPERF_REPOSITORY_ROOT.joinpath("deploy").joinpath("config"), endpoint
        )
        template = template_source_path.read_text()
        output = template.format(ptp_config=endpoint.benchmark.ptp_config, machine=endpoint.machine, cluster=endpoint.cluster)
        output_file = self.config_file_path
        output_file.write_text(output)
        return output_file


    @staticmethod
    def extract_sample_from_log_using_regex(endpoint: "PTPEndpoint", source_name: str, pattern: str, number_conversion: typing.Callable[[str], int] = int):
        """Search through records from specified endpoint and log source using pattern,
        ingesting samples from values in regex groups 'master_offset' and 'path_delay'"""
        from ptp_perf.models.sample import Sample

        # Since we use stdbuf for ptpd now we also need to use that as a source.
        logs: typing.List["LogRecord"] = endpoint.logrecord_set.filter(source=source_name).all()


        samples = []
        for log in logs:
            match = re.search(
                pattern=pattern,
                string=log.message,
            )
            if match is None:
                continue

            samples.append(
                Sample(
                    endpoint = endpoint,
                    # timestamp=timedelta(seconds=float(match.group("timestamp"))),
                    timestamp=log.timestamp,
                    sample_type=Sample.SampleType.CLOCK_DIFF,
                    value=number_conversion(match.group("master_offset")),
                )
            )

            samples.append(
                Sample(
                    endpoint=endpoint,
                    # timestamp=timedelta(seconds=float(match.group("timestamp"))),
                    timestamp=log.timestamp,
                    sample_type=Sample.SampleType.PATH_DELAY,
                    value=number_conversion(match.group("path_delay")),
                )
            )

        Sample.objects.bulk_create(samples)
        return samples
