import asyncio
import logging
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Optional

from adapters.benchmark_adapter import BenchmarkAdapter
from config import current_configuration
from invoke.invocation import Invocation
from profiles.base_profile import BaseProfile
from util import async_process_communicate, unpack_one_value_or_error


async def start_background_task(invocation: Invocation) -> Invocation:
    invocation.verify_return_code = False
    await invocation.start_async()
    invocation.communicate_in_background()
    return invocation


@dataclass()
class NetworkPerformanceDegrader(BenchmarkAdapter):
    target_bandwidth: Optional[str] = None
    iperf_invocation: Optional[Invocation] = None

    async def on_pre_benchmark_worker(self, benchmark_run: BaseProfile):
        server_address = unpack_one_value_or_error(
            [machine.address for machine in current_configuration.cluster.machines if machine.plugin_settings.iperf_server],
            "Exactly one machine should be specified as the iPerf server to use the network performance degrader plugin"
        )

        logging.info(f"Determined iperf server address: {server_address}")
        logging.info(f"Launching iperf on {len(current_configuration.cluster)} workers...")

        iperf_command = ["iperf", "-i", "1"]
        if self.target_bandwidth:
            iperf_command.append(f"--bandwidth={self.target_bandwidth}")

        if current_configuration.machine.plugin_settings.iperf_server:
            logging.info("Launching iPerf server...")
            self.iperf_invocation = await start_background_task(Invocation.of_command(*iperf_command, '-s'))
        else:
            logging.debug("Waiting momentarily for iPerf servers to come up...")
            await asyncio.sleep(0.5)
            logging.info("Launching iPerf clients...")
            self.iperf_invocation = await start_background_task(
                Invocation.of_command(*iperf_command, '-c', server_address, '-d', '-t', '0')
            )

    async def on_post_benchmark_worker(self, benchmark_run: BaseProfile):
        logging.info("Shutting down running iperf peers...")
        await self.iperf_invocation.terminate()

@dataclass()
class CPUPerformanceDegrader(BenchmarkAdapter):
    target_load: Optional[float] = None
    stress_ng_invocation: Optional[Invocation] = None

    async def on_pre_benchmark_worker(self, benchmark_run: BaseProfile):
        logging.info(f"Launching stress-ng on {len(current_configuration.cluster)} workers...")

        stress_ng_command = ["stress-ng", "-M"]
        if self.target_load:
            stress_ng_command += ["-l", self.target_load]

        logging.info("Launching stress_ng tasks...")
        self.stress_ng_invocation = await start_background_task(
            Invocation.of_command(*stress_ng_command, '-c', current_configuration.machine.plugin_settings.stress_ng_cpus)
        )

    async def on_post_benchmark_worker(self, benchmark_run: BaseProfile):
        logging.info("Shutting down running iperf peers...")
        await self.stress_ng_invocation.terminate()
