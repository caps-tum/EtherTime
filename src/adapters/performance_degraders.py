import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from config import current_configuration
from invoke.invocation import Invocation
from profiles.base_profile import BaseProfile
from util import unpack_one_value_or_error


@dataclass
class NetworkPerformanceDegrader:
    profile: BaseProfile
    iperf_invocation: Optional[Invocation] = None

    async def run(self):
        target_bandwidth = self.profile.benchmark.artificial_load_network
        dscp_priority = self.profile.benchmark.artificial_load_network_dscp_priority

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

        try:
            if current_configuration.machine.plugin_settings.iperf_server:
                logging.info("Launching iPerf server...")
                self.iperf_invocation = await Invocation.of_command(*iperf_command, '-s').run()
            else:
                logging.debug("Waiting momentarily for iPerf server to come up...")
                await asyncio.sleep(0.5)
                logging.info("Launching iPerf client...")
                # Launching clients
                self.iperf_invocation = await Invocation.of_command(
                    *iperf_command, '-c', server_address, '-d', '-t', '0'
                ).run()
        finally:
            # Attach log to profile raw data
            if self.iperf_invocation is not None:
                self.profile.raw_data.update(iperf_log=self.iperf_invocation.output)


@dataclass
class CPUPerformanceDegrader:
    profile: BaseProfile
    stressng_process: Optional[Invocation] = None

    async def run(self):
        target_load = self.profile.benchmark.artificial_load_cpu

        stress_ng_command = ["stress-ng", "-M"]
        if target_load is not None:
            stress_ng_command += ["-l", target_load]

        logging.info("Launching stress_ng tasks...")
        try:
            self.stressng_process = await Invocation.of_command(
                *stress_ng_command, '-c', current_configuration.machine.plugin_settings.stress_ng_cpus
            ).run()
        finally:
            # Attach log to profile raw data
            if self.stressng_process is not None:
                self.profile.raw_data.update(stressng_log=self.stressng_process.output)
