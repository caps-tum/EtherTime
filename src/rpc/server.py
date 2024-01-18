import asyncio
import logging
import threading
import typing
from typing import Callable, TypeVar, Generic, Iterable

import rpyc
from rpyc import ThreadedServer

import util
from rpc import settings
from rpc.server_service import RPCServerService
from rpc.client_service import RPCClientService
from rpc.rpc_target import RPCTarget

SERVER_SERVICE_TYPE = TypeVar("SERVER_SERVICE_TYPE", bound=RPCServerService)
CLIENT_SERVICE_TYPE = TypeVar("CLIENT_SERVICE_TYPE", bound=RPCClientService)

class RPCServer(Generic[SERVER_SERVICE_TYPE, CLIENT_SERVICE_TYPE]):
    server: ThreadedServer = None
    service_type: typing.Type = None
    server_thread: threading.Thread = None
    targets: dict[str, RPCTarget] = None

    @staticmethod
    def start_rpc_server():
        RPCServer.targets = dict()
        RPCServer.server = ThreadedServer(
            RPCServer.service_type, hostname="127.0.0.1", port=settings.RPC_PORT,
            protocol_config={"allow_public_attrs": True},
            logger=logging.Logger("RPC", logging.WARNING),
        )
        RPCServer.server_thread = threading.Thread(target=RPCServer.server.start)
        RPCServer.server_thread.start()

    @staticmethod
    def stop_rpc_server():
        if RPCServer.server is not None:
            logging.info("Shutting RPC server down...")
            RPCServer.server.close()
            RPCServer.server_thread.join()
            logging.info("RPC server cleanup completed.")

    @staticmethod
    def register_client(id: str, service: RPCServerService):
        RPCServer.targets[id]._rpc_server_service = service

    @staticmethod
    def unregister_client(id: str):
        RPCServer.targets[id]._rpc_server_service = None

    @staticmethod
    def num_identified_clients():
        return len([target for target in RPCServer.targets.values() if target.rpc_connected])

    @classmethod
    async def stop_rpc_clients(cls):
        await util.async_gather_with_progress(
            *(cls.remote_function_run_as_async(cls.get_remote_service(key).shutdown) for key in cls.targets),
            label="Shutting down RPC clients..."
        )

    @classmethod
    async def remote_function_run_as_async(cls, function: Callable, *args, **kwargs):
        async_function = rpyc.async_(function)
        task = async_function(*args, **kwargs)
        while not task.ready:
            await asyncio.sleep(1)
        return task.value

    @staticmethod
    def get_service(key: str) -> SERVER_SERVICE_TYPE:
        return RPCServer.targets[key]._rpc_server_service

    @staticmethod
    def get_remote_service(key: str) -> CLIENT_SERVICE_TYPE:
        return RPCServer.targets[key]._rpc_server_service.remote_service()

    @staticmethod
    async def start_remote_clients(targets: Iterable[RPCTarget]):
        logging.info("Connecting RPC clients...")
        for target in targets:
            RPCServer.targets[target.id] = target
            await target.rpc_start()

    @staticmethod
    async def wait_for_clients_connected():
        await util.async_wait_for_condition(
            lambda: RPCServer.check_client_identification_progress(),
            target=len(RPCServer.targets),
            label="Waiting for RPC clients to connect."
        )

    @staticmethod
    def check_client_identification_progress():
        # Fail if any client processes exited
        if any([target._rpc_ssh_connection._process.returncode is not None for target in RPCServer.targets.values()]):
            raise util.ImmediateException("Failed to launch RPC clients.")
        return RPCServer.num_identified_clients()
