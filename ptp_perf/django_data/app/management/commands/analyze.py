import logging
from argparse import ArgumentParser
from datetime import datetime

from django.core.management.base import BaseCommand

from ptp_perf import util, constants, config
from ptp_perf.models import PTPProfile
from ptp_perf.models.benchmark_summary import BenchmarkSummary
from ptp_perf.models.endpoint import ProfileCorruptError
from ptp_perf.models.exceptions import NoDataError
from ptp_perf.models.loglevel import LogLevel
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.vendor.registry import VendorDB


def analyze(force: bool = False):
    # profile_query = PTPProfile.objects.filter(is_processed=False).all()
    profile_query = PTPProfile.objects.all().filter(is_running=False)
    if not force:
        profile_query = profile_query.filter(is_processed=False)

    converted_profiles = 0

    for profile in profile_query:
        try:
            convert_profile(profile)
            BenchmarkSummary.invalidate(
                benchmark=profile.benchmark, vendor=profile.vendor, cluster=profile.cluster
            )
            converted_profiles += 1
        except Exception as e:
            profile.log_analyze(f"Failed to convert profile! {e}", level=LogLevel.ERROR)


    return converted_profiles

def convert_profile(profile: PTPProfile):
    """Parse the collected raw log data into a processable analyzed format."""

    total_samples = 0
    profile.clear_analysis_data()
    profile_endpoints = profile.ptpendpoint_set.all()
    for endpoint in profile_endpoints:
        parsed_samples = profile.vendor.parse_log_data(endpoint)
        profile.log_analyze(f"{endpoint} converted {len(parsed_samples)} samples.")
        total_samples += len(parsed_samples)

    try:
        parsed_faults = 0
        for endpoint in profile_endpoints:
            parsed_faults += endpoint.process_fault_data()

        if profile.benchmark.fault_location is not None and parsed_faults == 0:
            raise ProfileCorruptError(
                f"Benchmark {profile.benchmark} should have faults on {profile.benchmark.fault_location} "
                f"but no faults were found on profile {profile}"
            )

        for endpoint in profile_endpoints:
            endpoint.process_system_metrics_data()

        for endpoint in profile_endpoints:
            endpoint.process_timeseries_data()

        if total_samples == 0:
            raise ProfileCorruptError("No samples on entire profile, corrupt.")

        # Success
        profile.is_processed = True
        profile.save()

    except ProfileCorruptError as e:
        # This profile is probably corrupt.
        profile.is_processed = True
        profile.is_corrupted = True
        profile.save()
        profile.log_analyze(f"Profile marked as corrupt: {e}", level=LogLevel.ERROR)


def summarize(force: bool = False):
    for vendor in VendorDB.ANALYZED_VENDORS:
        for cluster in config.ANALYZED_CLUSTERS:
            for benchmark in cluster.supported_benchmarks():
                try:
                    BenchmarkSummary.create(
                        benchmark, vendor, cluster, force_update=force,
                    )
                except NoDataError:
                    pass


def run_analysis(force: bool, run_analyze: bool = True, run_summarize: bool = True):

    if run_analyze:
        start_time = datetime.now()
        converted_profiles = analyze(force=force)
        completion_time = datetime.now()
        logging.info(f"Analysis of {converted_profiles} profiles completed in {completion_time - start_time}.")
    if run_summarize:
        summarize(force=force)


class Command(BaseCommand):
    help = "Analyzes profiles"

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("--force", action='store_true', help="Force analysis of all profiles, even if they were already analyzed.")

    def handle(self, *args, **options):
        util.setup_logging()

        force = options["force"]

        with util.StackTraceGuard():
            run_analysis(force)
