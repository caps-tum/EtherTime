import asyncio
import logging

from ptp_perf.invoke.invocation import Invocation, InvocationFailedException
from ptp_perf.machine import Machine, Cluster
from ptp_perf.util import setup_logging, async_gather_with_progress


async def restart_node(machine: Machine):
    await machine.invoke_ssh(
        "sudo shutdown -r now"
    ).hide_unless_failure().run(timeout=10)
    await asyncio.sleep(3)

    success: bool = False
    i = 0
    for i in range(20):
        try:
            await machine.invoke_ssh(
                "echo '$(date): Restart OK'"
            ).hide().run(timeout=10)
            success=True
            break
        except TimeoutError:
            pass
        except InvocationFailedException:
            pass
        await asyncio.sleep(1)

    if success:
        logging.info(f"Machine {machine} restarted successfully.")
    else:
        logging.warning(f"Machine {machine} not restarted successfully, ({i} connection failures).")


async def restart_cluster(cluster: Cluster):
    logging.info(f"Restarting cluster ({len(cluster.machines)} nodes)...")
    await async_gather_with_progress(*[restart_node(machine) for machine in cluster.machines], label="Restarting machines")

