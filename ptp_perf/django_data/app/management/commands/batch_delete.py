import asyncio
import re

from django.core.management.base import BaseCommand

from ptp_perf import util
from ptp_perf.config import get_configuration_by_cluster_name
from ptp_perf.models import PTPProfile
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.util import str_join, user_prompt_confirmation


class Command(BaseCommand):
    help = "Tool to batch delete profiles."

    def add_arguments(self, parser):
        parser.add_argument(
            "--benchmark-regex", type=str, required=True,
            help="A regex to filter benchmark ids for."
        )

    def handle(self, *args, **options):
        util.setup_logging()

        benchmark_regex = options['benchmark_regex']
        matched_benchmarks = [benchmark.id for benchmark in BenchmarkDB.all() if re.match(benchmark_regex, benchmark.id)]
        print(f"Matched {len(matched_benchmarks)} benchmarks: {str_join(matched_benchmarks)}")

        profiles = PTPProfile.objects.filter(benchmark_id__in=matched_benchmarks)

        if profiles.count() == 0:
            print(f"No matches for regex: '{benchmark_regex}'")
            return

        for profile in profiles:
            print(profile)
        user_prompt_confirmation(f"Do you want to delete these {len(profiles)} profiles?")

        profiles.delete()
        print(f"Deleted profiles.")
