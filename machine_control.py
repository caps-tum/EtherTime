import asyncio
import logging
import re
from argparse import ArgumentParser

from ptp_perf.invoke.invocation import InvocationFailedException
from ptp_perf.utilities.django_utilities import bootstrap_django_environment

bootstrap_django_environment()

from ptp_perf import config
from ptp_perf.util import str_join, user_prompt_confirmation, setup_logging


async def run_on_machines(command: str, machine_regex: str = '.*', ask_confirmation: bool = True):
    machines = [
        machine for machine in config.ANALYZED_MACHINES
        if re.search(machine_regex, machine.id) is not None
           or re.search(machine_regex, machine.name) is not None
    ]

    print(f"Invoking command on {len(machines)} machines: {command}")
    print(f"Machines: {str_join(machines)}")

    if ask_confirmation:
        user_prompt_confirmation(f"Command: {command}")

    failures = 0
    for machine in machines:
        try:
            await machine.invoke_ssh(
                command,
                ssh_options=["-o", "ConnectTimeout=3", "-o", "ConnectTimeout=3"]
            ).run()
        except InvocationFailedException as e:
            logging.warning(f"Machine {machine}: {e}")
            failures += 1

    print(f"Result: {failures} failures / {len(machines)} invocations.")

if __name__ == '__main__':
    setup_logging()
    parser = ArgumentParser(description='Run commands on multiple machines via SSH. Convenience function for managing machines on a cluster.')
    parser.add_argument(
        "--regex", type=str, default='.*',
        help="Filter machines via a regular expression. Matches any part of the machine id or name by default."
             "Use ^ and $ regex characters to limit match to the entire expression. "
    )
    parser.add_argument("command", type=str, help="Command to run remotely")
    result = parser.parse_args()

    asyncio.run(run_on_machines(command=result.command, machine_regex=result.regex))
