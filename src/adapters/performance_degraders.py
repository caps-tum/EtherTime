import asyncio
import logging
from typing import Optional

from config import current_configuration
from invoke.invocation import Invocation
from profiles.base_profile import BaseProfile
from util import unpack_one_value_or_error


async def start_background_task(invocation: Invocation) -> Invocation:
    invocation.verify_return_code = False
    await invocation.start_async()
    invocation.communicate_in_background()
    return invocation


class NetworkPerformanceDegrader:
    iperf_invocation: Optional[Invocation] = None

    async def start(self, target_bandwidth: Optional[int], dscp_priority: Optional[str] = None):
        server_address = unpack_one_value_or_error(
            [worker.plugin_settings.iperf_address for worker in current_configuration.cluster.machines if worker.plugin_settings.iperf_server],
            "Exactly one worker should be specified as the iPerf server to use the network performance degrader plugin"
        )

        logging.debug(f"Determined iperf server address: {server_address}")

        iperf_command = ["iperf", "-i", "1"]
        if target_bandwidth:
            iperf_command.append(f"--bandwidth={target_bandwidth}M")
        if dscp_priority:
            iperf_command.append(f"--tos={dscp_priority}")

        if current_configuration.machine.plugin_settings.iperf_server:
            logging.info("Launching iPerf server...")
            self.iperf_invocation = await start_background_task(Invocation.of_command(*iperf_command, '-s'))
        else:
            logging.debug("Waiting momentarily for iPerf server to come up...")
            await asyncio.sleep(0.5)
            logging.info("Launching iPerf client...")
            # Launching clients
            self.iperf_invocation = await start_background_task(
                Invocation.of_command(*iperf_command, '-c', server_address, '-d', '-t', '0'),
            )

    async def stop(self):
        logging.info("Shutting down running iperf peers...")
        await self.iperf_invocation.terminate(timeout=5)


class CPUPerformanceDegrader:
    stressng_process: Optional[Invocation] = None

    async def start(self, target_load: Optional[int]):

        stress_ng_command = ["stress-ng", "-M"]
        if target_load is not None:
            stress_ng_command += ["-l", target_load]

        logging.info("Launching stress_ng tasks...")
        for machine in current_configuration.cluster.machines:
            self.stressng_process = await start_background_task(
                Invocation.of_command(*stress_ng_command, '-c', machine.plugin_settings.stress_ng_cpus)
            )


    async def stop(self):
        logging.info("Shutting down running stress_ng...")
        await self.stressng_process.terminate(timeout=5)
