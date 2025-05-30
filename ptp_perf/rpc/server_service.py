import logging
import typing

import rpyc

if typing.TYPE_CHECKING:
    from ptp_perf.rpc.client_service import RPCClientService


class RPCServerService(rpyc.Service):
    connection: rpyc.Connection = None
    identifier: str = None

    def on_connect(self, conn: rpyc.Connection):
        super().on_connect(conn)
        self.connection = conn

    def on_disconnect(self, conn):
        super().on_disconnect(conn)
        from ptp_perf.rpc.server import RPCServer
        RPCServer.unregister_client(self.identifier)

    @rpyc.exposed
    def connection_id(self, id: str):
        self.identifier = id
        from ptp_perf.rpc.server import RPCServer
        RPCServer.register_client(id, self)
        logging.debug(f"RPC client identified: {id}")

    def remote_service(self) -> "RPCClientService":
        return self.connection.root

    def shutdown(self):
        self.remote_service().shutdown()

