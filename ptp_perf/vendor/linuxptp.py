import logging
import re
import typing
from dataclasses import dataclass
from datetime import timedelta

from ptp_perf.invoke.invocation import Invocation
from ptp_perf.utilities import units
from ptp_perf.utilities.multi_task_controller import MultiTaskController
from ptp_perf.vendor.vendor import Vendor

if typing.TYPE_CHECKING:
    from ptp_perf.models import PTPEndpoint, Sample


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

    async def run(self, endpoint: "PTPEndpoint"):
        machine = endpoint.machine

        background_tasks = MultiTaskController()

        self._process_ptp4l = Invocation.of_command(
            "ptp4l", "-i", machine.ptp_interface, "-m",
            "-f", str(self.config_file_path), # Config file
        ).append_arg_if_present(
            "-s", condition=not machine.ptp_master,
        ).append_arg_if_present(
            "-S", condition=machine.ptp_software_timestamping
        ).as_privileged()
        self._process_ptp4l.keep_alive = endpoint.benchmark.ptp_keepalive
        self._process_ptp4l.restart_delay = endpoint.benchmark.ptp_restart_delay
        background_tasks.add_task(self._process_ptp4l.run_as_task())

        if machine.ptp_use_phc2sys:
            self._process_phc2sys = Invocation.of_command(
                "phc2sys", "-m", "-a", "-r",
            ).append_arg_if_present(
                # We append -r a *second* time on master.
                # This allows not only phc --> sys but also sys --> phc, which we want on the master.
                "-r", condition=machine.ptp_master,
            ).as_privileged()
            self._process_phc2sys.keep_alive = endpoint.benchmark.ptp_keepalive
            self._process_ptp4l.restart_delay = endpoint.benchmark.ptp_restart_delay
            background_tasks.add_task(self._process_phc2sys.run_as_task())
        try:
            await background_tasks.run_for()
        finally:
            await background_tasks.cancel_pending_tasks()

    async def restart(self, kill: bool = True):
        await self._process_ptp4l.restart(kill, ignore_return_code=True)
        if self._process_phc2sys is not None:
            await self._process_phc2sys.restart(kill, ignore_return_code=True)


    @property
    def install_supported(self):
        return super().install_supported

    def install(self):
        self.invoke_package_manager("linuxptp")

    def uninstall(self):
        self.invoke_package_manager("linuxptp", action="purge")

    def parse_log_data(self, endpoint: "PTPEndpoint") -> typing.List["Sample"]:
        from ptp_perf.models.sample import Sample

        if endpoint.logrecord_set.filter(source="phc2sys").count() > 0:
            raise NotImplementedError("Cannot import phc2sys log for the moment.")

        logs = endpoint.logrecord_set.filter(source="ptp4l").all()

        samples = []
        for log in logs:
            match = re.search(
                pattern="ptp4l\[(?P<timestamp>[0-9.+-]+)\]: master offset \s*(?P<master_offset>[0-9.+-]+)\s* s\d+ freq \s*(?P<s0_freq>[0-9.+-]+)\s* path delay\s* (?P<path_delay>[0-9.+-]+)",
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
                    value=int(match.group("master_offset")),
                )
            )

            samples.append(
                Sample(
                    endpoint=endpoint,
                    # timestamp=timedelta(seconds=float(match.group("timestamp"))),
                    timestamp=log.timestamp,
                    sample_type=Sample.SampleType.PATH_DELAY,
                    value=int(match.group("path_delay")),
                )
            )

        Sample.objects.bulk_create(samples)
        return samples

    @property
    def running(self):
        if self._process_ptp4l is not None:
            return self._process_ptp4l.running
        return False
