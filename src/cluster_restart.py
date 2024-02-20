import asyncio
import logging

from config import current_configuration
from invoke.invocation import Invocation, InvocationFailedException
from machine import Machine, Cluster
from util import setup_logging, async_gather_with_progress


async def restart_node(machine: Machine):
    await Invocation.of_command(
        "ssh", machine.address, "sudo shutdown -r now"
    ).run(timeout=10)
    await asyncio.sleep(3)

    success: bool = False
    for i in range(20):
        try:
            await Invocation.of_command(
                "ssh", machine.address, "echo '$(date): Restart OK'"
            ).run(timeout=10)
            success=True
            break
        except TimeoutError:
            logging.info(f"Connection to {machine} failed.")
        except InvocationFailedException:
            logging.info(f"Connection to {machine} failed.")
        await asyncio.sleep(1)

    if success:
        logging.info(f"Machine {machine} restarted successfully.")
    else:
        logging.warning(f"Machine {machine} not restarted successfully, timeout.")

async def restart_cluster(cluster: Cluster):
    await async_gather_with_progress(*[restart_node(machine) for machine in cluster.machines], label="Restarting machines")

if __name__ == "__main__":
    setup_logging()

    asyncio.run(restart_cluster(current_configuration.cluster))
