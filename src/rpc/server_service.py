import logging
import typing

import rpyc

if typing.TYPE_CHECKING:
    from rpc.client_service import RPCClientService


class RPCServerService(rpyc.Service):
    connection: rpyc.Connection = None
    identifier: str = None

    def on_connect(self, conn: rpyc.Connection):
        super().on_connect(conn)
        self.connection = conn

    def on_disconnect(self, conn):
        super().on_disconnect(conn)
        from rpc.server import RPCServer
        RPCServer.unregister_client(self.identifier)

    @rpyc.exposed
    def connection_id(self, id: str):
        self.identifier = id
        from rpc.server import RPCServer
        RPCServer.register_client(id, self)
        logging.info(f"RPC client identified: {id}")

    def remote_service(self) -> "RPCClientService":
        return self.connection.root

    def shutdown(self):
        self.remote_service().shutdown()

