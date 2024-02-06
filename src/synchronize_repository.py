import asyncio
from argparse import ArgumentParser

import util
from config import current_configuration, get_configuration_by_cluster_name

if __name__ == '__main__':
    util.setup_logging()

    parser = ArgumentParser(description="Tool to deploy the repository source code to remote machines using rsync.")
    parser.add_argument("--config", type=str, default=None, help="The name of the cluster configuration to use. Uses the default cluster if not specified.")
    result = parser.parse_args()

    configuration_name = result.config
    cluster = current_configuration.cluster if configuration_name is None else get_configuration_by_cluster_name(configuration_name).cluster
    asyncio.run(
        util.async_gather_with_progress(
            *[machine.synchronize_repository() for machine in cluster.machines],
            label="Synchronizing repositories",
        )
    )
