import asyncio
from argparse import ArgumentParser

import rpyc

import benchmark
import config
import util
from profiles.base_profile import BaseProfile
from rpc.client_service import RPCClientService


@rpyc.service
class PTPPerfRPCClient(RPCClientService):

    def __init__(self, client_id: str):
        super().__init__(client_id)
        config.set_machine(client_id)

    @rpyc.exposed
    def benchmark(self, profile: str) -> str:
        profile_obj = BaseProfile.load_str(profile)
        return asyncio.run(benchmark.benchmark(profile_obj)).dump()


if __name__ == '__main__':
    util.setup_logging()

    # This proxy program is necessary so that the client is start from the root of the python project and no messing with the PYTHONPATH is necessary.
    parser = ArgumentParser(
        description="Client RPC program that executes PTP-Perf functions on behalf of the orchestrator. "
                    "This program should not be run by the user, it is invoked by the orchestrator. "
                    "Connects to the orchestrator via RPC using host:port and requires a client id provided by the orchestrator."
    )
    parser.add_argument("--host", type=str, required=True, help="RPC server address to connect to.")
    parser.add_argument("--port", type=int, default=1234, help="RPC server port to connect to.")
    parser.add_argument("--id", type=str, required=True, help="The worker identifier to use.")

    result = parser.parse_args()
    service = PTPPerfRPCClient(result.id)

    with util.StackTraceGuard():
        service.run_rpc_client(result.host, result.port)