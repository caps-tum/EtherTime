import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from ptp_perf import config
from ptp_perf.invoke.invocation import Invocation
from ptp_perf.models import PTPEndpoint
from ptp_perf.util import unpack_one_value_or_error


@dataclass
class NetworkPerformanceDegrader:
    endpoint: PTPEndpoint
    iperf_invocation: Optional[Invocation] = None

    async def run(self):
        target_bandwidth = self.endpoint.benchmark.artificial_load_network
        dscp_priority = self.endpoint.benchmark.artificial_load_network_dscp_priority

        worker = unpack_one_value_or_error(
            [worker for worker in self.endpoint.cluster.machines
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
            await self.wait_for_port_open(server_address, 5001)
            logging.info("Launching iPerf client...")
            # Launching clients
            self.iperf_invocation = Invocation.of_command(
                *iperf_command, '-c', server_address, '-d', '-t', '0'
            )

        await self.iperf_invocation.run()

    @staticmethod
    async def wait_for_port_open(host, port, interval=3, retries=10):
        """
        Asynchronously wait for a port on a host to be open.

        :param host: The hostname or IP address of the server to check.
        :param port: The port number to check.
        :param interval: Interval in seconds between checks.
        """
        for _ in range(retries):
            try:
                # Attempt to open a connection to the specified port
                reader, writer = await asyncio.open_connection(host, port)
                # If connection is successful, close it and return
                writer.close()
                await writer.wait_closed()
                logging.debug(f"Port {port} on {host} is now open!")
                return
            except (ConnectionRefusedError, OSError):
                # If connection fails, wait for the interval and then retry
                logging.debug(f"Port {port} on {host} is closed, retrying in {interval} seconds...")
                await asyncio.sleep(interval)
        raise RuntimeError(f"Cannot connect to {host}:{port} after {retries} retries.")

@dataclass
class StressNGPerformanceDegrader:
    endpoint: PTPEndpoint
    stressng_process: Optional[Invocation] = None

    async def run(self):
        target_load_cpu = self.endpoint.benchmark.artificial_load_cpu

        stress_ng_command = ["stress-ng", "--metrics", "--timestamp", "--timeout", "1h"]
        if target_load_cpu > 0:
            stress_ng_command += [
                '--cpu', str(self.endpoint.machine.plugin_settings.stress_ng_cpus),
                "--cpu-load", str(target_load_cpu)
            ]

            if self.endpoint.benchmark.artificial_load_cpu_restrict_cores:
                stress_ng_command += ["--taskset", self.endpoint.machine.plugin_settings.stress_ng_cpu_restrict_cores]
            if self.endpoint.benchmark.artificial_load_cpu_scheduler is not None:
                stress_ng_command += ["--sched", self.endpoint.benchmark.artificial_load_cpu_scheduler]

        elif self.endpoint.benchmark.artificial_load_aux:
            stress_ng_command += self.endpoint.benchmark.artificial_load_aux_options
        else:
            raise RuntimeError("Unsupported Stress-NG mode")

        logging.info("Launching stress_ng tasks...")
        self.stressng_process = Invocation.of_command(
            *stress_ng_command,
        )
        await self.stressng_process.run()
