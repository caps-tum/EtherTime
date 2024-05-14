import typing
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from ptp_perf.invoke.invocation import Invocation
from ptp_perf.machine import MachineClientType
from ptp_perf.vendor.vendor import Vendor

if typing.TYPE_CHECKING:
    from ptp_perf.models import PTPEndpoint, Sample


@dataclass
class SPTPVendor(Vendor):
    id: str = "sptp"
    name: str = "SPTP"
    _process: Invocation = None

    def running(self):
        if self._process is not None:
            return self._process.running
        return False

    @property
    def installed(self):
        return self.check_executable_present("~/go/bin/sptp")

    def install(self):
        raise NotImplementedError()

    def uninstall(self):
        raise NotImplementedError()

    async def run(self, endpoint: "PTPEndpoint"):

        effective_client_type = endpoint.get_effective_client_type()
        if effective_client_type == MachineClientType.FAILOVER_MASTER:
            raise NotImplementedError()

        executable = {
            MachineClientType.MASTER: "ptp4u",
            MachineClientType.SLAVE: "sptp",
        }[effective_client_type]
        self._process = Invocation.of_command(
            executable, "-iface", endpoint.machine.ptp_interface,
        ).set_environment_variable(
            "PATH", str(Path(endpoint.machine.remote_root).joinpath(f"../go/bin/")), extend=True
        ).as_privileged()

        if effective_client_type.is_primary_master():
            if endpoint.machine.ptp_software_timestamping:
                self._process.append_arg_if_present("--timestamptype")
                self._process.append_arg_if_present("software")
        elif effective_client_type.is_slave():
            self._process.append_arg_if_present("-config")
            self._process.append_arg_if_present(str(self.config_file_path)),
            self._process.append_arg_if_present(endpoint.cluster.ptp_master.ptp_address)
        else:
            raise NotImplementedError()

        # SPTP exits with return code -15 if it gets cancelled
        self._process.expected_return_codes.append(-15)
        self._process.keep_alive = endpoint.benchmark.ptp_keepalive

        await self._process.run()

    async def restart(self, kill: bool = True, restart_delay: timedelta = timedelta(seconds=1)):
        await self._process.restart(kill, ignore_return_code=True, restart_delay=restart_delay)

    def config_file_source_path(self, base_path: Path, endpoint: "PTPEndpoint") -> Path:
        effective_client_type = endpoint.get_effective_client_type()
        return {
            MachineClientType.MASTER: base_path.joinpath("sptp_template_master.conf"),
            MachineClientType.SLAVE: base_path.joinpath("sptp_template_slave.conf"),
        }[effective_client_type]

    @classmethod
    def parse_log_data(cls, endpoint: "PTPEndpoint") -> typing.List["Sample"]:
        return Vendor.extract_sample_from_log_using_regex(
            endpoint,
            source_name='sptp',
            pattern='msg="offset \s*(?P<master_offset>[0-9.+-]+)\s* s\d+ freq \s*(?P<s0_freq>[0-9.+-]+)\s* path delay\s* (?P<path_delay>[0-9.+-]+) \(\s*[0-9.+-]+:\s*[0-9.+-]+\)"',
        )

    def get_processes(self) -> typing.Iterable[Invocation]:
        return (self._process, )
