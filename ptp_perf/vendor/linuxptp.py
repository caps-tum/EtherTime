import logging
import re
import typing
from dataclasses import dataclass
from datetime import timedelta

from ptp_perf.invoke.invocation import Invocation
from ptp_perf.machine import MachineClientType
from ptp_perf.utilities import units
from ptp_perf.utilities.multi_task_controller import MultiTaskController
from ptp_perf.vendor.vendor import Vendor

if typing.TYPE_CHECKING:
    from ptp_perf.models import PTPEndpoint, Sample


@dataclass
class LinuxPTPVendor(Vendor):
    id: str = "linuxptp"
    name: str = "PTP4L"

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

        effective_client_type = machine.get_effective_client_type(failover_active=endpoint.benchmark.fault_failover)
        self._process_ptp4l = Invocation.of_command(
            "ptp4l", "-i", machine.ptp_interface, "-m",
            "-f", str(self.config_file_path), # Config file
        ).append_arg_if_present(
            "-s", condition=effective_client_type == MachineClientType.SLAVE,
        ).append_arg_if_present(
            "-S", condition=machine.ptp_software_timestamping
        ).as_privileged()
        self._process_ptp4l.keep_alive = endpoint.benchmark.ptp_keepalive
        background_tasks.add_task(self._process_ptp4l.run_as_task())

        if machine.ptp_use_phc2sys:
            self._process_phc2sys = Invocation.of_command(
                "phc2sys", "-m", "-a", "-r",
            ).append_arg_if_present(
                # We append -r a *second* time on master.
                # This allows not only phc --> sys but also sys --> phc, which we want on the master.
                "-r", condition=effective_client_type.is_master_or_failover(),
            ).as_privileged()
            self._process_phc2sys.keep_alive = endpoint.benchmark.ptp_keepalive
            background_tasks.add_task(self._process_phc2sys.run_as_task())
        try:
            await background_tasks.run_for()
        finally:
            await background_tasks.cancel_pending_tasks()

    async def restart(self, kill: bool = True, restart_delay: timedelta = timedelta(seconds=1)):
        await self._process_ptp4l.restart(kill, ignore_return_code=True, restart_delay=restart_delay)
        if self._process_phc2sys is not None:
            await self._process_phc2sys.restart(kill, ignore_return_code=True, restart_delay=restart_delay)


    @property
    def install_supported(self):
        return super().install_supported

    def install(self):
        self.invoke_package_manager("linuxptp")

    def uninstall(self):
        self.invoke_package_manager("linuxptp", action="purge")

    def parse_log_data(self, endpoint: "PTPEndpoint") -> typing.List["Sample"]:
        results = Vendor.extract_sample_from_log_using_regex(
            endpoint,
            source_name='ptp4l',
            pattern="ptp4l\[(?P<timestamp>[0-9.+-]+)\]: master offset \s*(?P<master_offset>[0-9.+-]+)\s* s\d+ freq \s*(?P<s0_freq>[0-9.+-]+)\s* path delay\s* (?P<path_delay>[0-9.+-]+)",
        )

        # Unsupported, offsets need to be added to each other
        # results += Vendor.extract_sample_from_log_using_regex(
        #     endpoint,
        #     source_name='phc2sys',
        #     pattern="phc2sys\[(?P<timestamp>[0-9.+-]+)\]: master offset \s*(?P<master_offset>[0-9.+-]+)\s* s\d+ freq \s*(?P<s0_freq>[0-9.+-]+)\s* path delay\s* (?P<path_delay>[0-9.+-]+)",
        # )

        return results


    @property
    def running(self):
        if self._process_ptp4l is not None:
            return self._process_ptp4l.running
        return False
