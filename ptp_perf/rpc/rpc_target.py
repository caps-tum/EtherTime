import asyncio
from asyncio import Task
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, ClassVar

from pydantic import PrivateAttr

from ptp_perf.invoke.invocation import Invocation
from ptp_perf.rpc import settings
from ptp_perf.rpc.server_service import RPCServerService
from ptp_perf.rpc.settings import rpc_get_local_root
from ptp_perf.util import PathOrStr


@dataclass(kw_only=True)
class RPCTarget:
    id: str
    address: str
    user: Optional[str] = None
    remote_root: str = rpc_get_local_root()
    deploy_root: bool = True

    # Omit type annotations so that pydantic ignores these fields :/
    _rpc_ssh_connection = None
    _rpc_server_service = None

    async def rpc_start(self):
        # Copy code changes to remote before launching RPC
        if self.deploy_root:
            await self.synchronize_repository()

        self._rpc_ssh_connection = Invocation.of_command(
            "ssh",
            "-o", "ServerAliveInterval=300",
            "-R", f"127.0.0.1:{settings.RPC_PORT}:127.0.0.1:{settings.RPC_PORT}", self.address,
            f"cd '{self.remote_root}/src' && "
            f"python3 rpc_client.py --host '127.0.0.1' --port {settings.RPC_PORT} --id '{self.id}'"
        )
        self._rpc_ssh_connection.run_as_task()

    async def rpc_stop(self):
        if self._rpc_server_service is not None:
            self._rpc_server_service.remote_service().shutdown()
        if self._rpc_ssh_connection is not None:
            await self._rpc_ssh_connection.wait(terminate_after=3)
        self._rpc_ssh_connection = None


    async def synchronize_repository(self):
        return await self.synchronize_rsync(rpc_get_local_root(), upload=True)

    async def synchronize_rsync(self, path: PathOrStr, upload: bool = True, mkpath: bool = False):
        """Copy the local path to this worker using rsync.
        :param path: should be inside the DDSPERF_REPOSITORY_ROOT, so that it can be resolved both locally and remotely.
        :param upload: if False, it downloads the specified path rather than uploading it.
        :param mkpath: The mkpath argument is passed to rsync.
        :return: Whether a copy operation actually took place.
        """

        rsync_args = ["rsync", "-av", "--exclude-from", f".rsync-filter", "--delete"]
        if mkpath:
            rsync_args.append("--mkpath")

        source_and_destination = [f"{path}/", f"{self.format_remote_path_reference(self.resolve_path(path))}/"]
        if not upload:
            source_and_destination.reverse()

        await Invocation.of_command(
            *rsync_args,
            *source_and_destination
        ).set_working_directory(rpc_get_local_root()).hide_unless_failure().run()

    def format_remote_path_reference(self, path: PathOrStr):
        return f"{self.formatted_address}:{path}"

    def resolve_path(self, path: PathOrStr) -> Path:
        str_path = str(path)
        for key, value in self.translate_paths.items():
            str_path = str_path.replace(str(key), str(value))
        return Path(str_path)

    @property
    def translate_paths(self) -> Dict[str, str]:
        return {rpc_get_local_root(): self.remote_root}

    @property
    def formatted_address(self):
        if self.user:
            return f"{self.user}@{self.address}"
        return self.address

    @property
    def rpc_connected(self):
        return self._rpc_server_service is not None

    @property
    def rpc_connection_closed(self):
        return not self._rpc_ssh_connection.running
