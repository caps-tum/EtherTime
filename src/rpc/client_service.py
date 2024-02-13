import logging

import rpyc

@rpyc.service
class RPCClientService(rpyc.Service):
    connection: rpyc.Connection = None
    client_id: str
    running: bool

    def __init__(self, client_id: str):
        super().__init__()
        self.client_id = client_id
        self.running = True


    def run_rpc_client(self, host: str, port: int):
        """Connect to a remote rpc server at host:port and run until completion."""
        self.connection = rpyc.connect(host, port, service=self)
        logging.debug("RPC connection established.")
        self.connection.root.connection_id(self.client_id)

        try:
            while self.running:
                served_requests = self.connection.poll(timeout=1)

                # Test connectivity. If ping fails, raises exception
                if not served_requests:
                    self.connection.ping()

        except Exception as e:
            logging.warning(f"RPC connection error: {e}. Shutting down.")

        self.finalize()

    @rpyc.exposed
    def shutdown(self):
        """Shutdown this worker by a remote command."""
        self.running = False

    def finalize(self):
        """Terminate this RPC client, either because of regular shutdown or because of an error."""
        logging.info("Exiting RPC.")
        self.connection.close()
        self.running = False
