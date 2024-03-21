import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from ptp_perf import config
from ptp_perf.invoke.invocation import Invocation
from ptp_perf.models import PTPEndpoint
from ptp_perf.profiles.base_profile import BaseProfile
from ptp_perf.util import unpack_one_value_or_error


@dataclass
class NetworkPerformanceDegrader:
    endpoint: PTPEndpoint
    iperf_invocation: Optional[Invocation] = None

    async def run(self):
        target_bandwidth = self.endpoint.benchmark.artificial_load_network
        dscp_priority = self.endpoint.benchmark.artificial_load_network_dscp_priority

        worker = unpack_one_value_or_error(
            [worker for worker in config.machines.values()
             if worker.plugin_settings is not None and worker.plugin_settings.iperf_server],
            "Exactly one worker should be specified as the iPerf server to use the network performance degrader plugin"
        )
        if self.endpoint.benchmark.artificial_load_network_secondary_interface:
            server_address = worker.plugin_settings.iperf_secondary_address
        else:
            server_address = worker.plugin_settings.iperf_address


        logging.debug(f"Determined iperf server address: {server_address}")

        iperf_command = ["iperf", "-i", "1"]
        if target_bandwidth:
            iperf_command.append(f"--bandwidth={target_bandwidth}M")
        if dscp_priority:
            iperf_command.append(f"--tos={dscp_priority}")

        if self.endpoint.machine.plugin_settings.iperf_server:
            logging.info("Launching iPerf server...")
            self.iperf_invocation = Invocation.of_command(*iperf_command, '-s')
        else:
            logging.debug("Waiting momentarily for iPerf server to come up...")
            await asyncio.sleep(0.5)
            logging.info("Launching iPerf client...")
            # Launching clients
            self.iperf_invocation = Invocation.of_command(
                *iperf_command, '-c', server_address, '-d', '-t', '0'
            )

        await self.iperf_invocation.run()


@dataclass
class CPUPerformanceDegrader:
    endpoint: PTPEndpoint
    stressng_process: Optional[Invocation] = None

    async def run(self):
        target_load = self.endpoint.benchmark.artificial_load_cpu

        stress_ng_command = ["stress-ng", "--metrics", "--timestamp", "--timeout", "0"]
        if target_load is not None:
            stress_ng_command += ["--cpu-load", str(target_load)]
        if self.endpoint.benchmark.artificial_load_cpu_restrict_cores:
            stress_ng_command += ["--taskset", self.endpoint.machine.plugin_settings.stress_ng_cpu_restrict_cores]
        if self.endpoint.benchmark.artificial_load_cpu_scheduler is not None:
            stress_ng_command += ["--sched", self.endpoint.benchmark.artificial_load_cpu_scheduler]


        logging.info("Launching stress_ng tasks...")
        self.stressng_process = Invocation.of_command(
            *stress_ng_command, '--cpu', str(self.endpoint.machine.plugin_settings.stress_ng_cpus)
        )
        await self.stressng_process.run()
