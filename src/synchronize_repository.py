import asyncio

import util
from config import current_configuration

if __name__ == '__main__':
    util.setup_logging()

    asyncio.run(
        util.async_gather_with_progress(
            *[machine.synchronize_repository() for machine in current_configuration.cluster.machines],
            label="Synchronizing repositories",
        )
    )
