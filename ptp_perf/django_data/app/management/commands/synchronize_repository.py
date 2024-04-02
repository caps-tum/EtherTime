import asyncio
import logging
from datetime import datetime

from django.core.management.base import BaseCommand

from ptp_perf import util, constants
from ptp_perf.config import get_configuration_by_cluster_name


class Command(BaseCommand):
    help = "Tool to deploy the repository source code to remote machines using rsync."

    def add_arguments(self, parser):
        parser.add_argument(
            "--config", type=str, required=True,
            help="The name of the cluster configuration to use."
        )

    def handle(self, *args, **options):
        util.setup_logging()

        configuration_name = options['config']
        cluster = get_configuration_by_cluster_name(configuration_name).cluster

        asyncio.run(
            util.async_gather_with_progress(
                *[machine.synchronize_repository() for machine in cluster.machines],
                label="Synchronizing repositories",
            )
        )
