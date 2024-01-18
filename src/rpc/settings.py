
def rpc_get_local_root() -> str:
    import constants
    return str(constants.get_repository_root())

RPC_PORT = 1245
