import logging
from argparse import ArgumentParser
from datetime import datetime

from django.core.management.base import BaseCommand

from ptp_perf import util, constants
from ptp_perf.models import PTPProfile


def analyze(force: bool = False):
    # profile_query = PTPProfile.objects.filter(is_processed=False).all()
    profile_query = PTPProfile.objects.all().filter(is_running=False)
    if not force:
        profile_query = profile_query.filter(is_processed=False)

    converted_profiles = 0

    for profile in profile_query:
        try:
            convert_profile(profile)
            converted_profiles += 1
        except Exception as e:
            logging.exception("Failed to convert profile!", exc_info=e)


    return converted_profiles

def convert_profile(profile: PTPProfile):

    # logging.info(
    #     f"Converting {profile.file_path_relative} "
    #     f"([Folder]({profile.storage_base_path.relative_to(constants.MEASUREMENTS_DIR)}), "
    #     f"[Chart]({profile.get_chart_timeseries_path().relative_to(constants.MEASUREMENTS_DIR)}), "
    #     f"[Convergence Chart]({profile.get_chart_timeseries_path(convergence_included=True).relative_to(constants.MEASUREMENTS_DIR)}))"
    # )

    total_samples = 0
    for endpoint in profile.ptpendpoint_set.all():
        # Remove existing data
        endpoint.sample_set.all().delete()
        parsed_samples = profile.vendor.parse_log_data(endpoint)
        logging.info(f"{endpoint} converted {len(parsed_samples)} samples.")

        endpoint.process_timeseries_data()

        endpoint.process_fault_data()

        total_samples += len(parsed_samples)

    if total_samples == 0:
        logging.warning("No samples on entire profile, corrupt.")
        profile.is_corrupted = True
    profile.is_processed = True
    profile.save()
    # processed_profile = profile.vendor.convert_profile(profile)
    # if processed_profile is not None:
    #     # Remove existing processed profiles (they may be in a different path)
    #     processed_profile.get_file_path(ProfileType.PROCESSED).unlink(missing_ok=True)
    #     processed_profile.get_file_path(ProfileType.PROCESSED_CORRUPT).unlink(missing_ok=True)
    #
    #     processed_profile.save()
    #
    #     processed_profile.create_timeseries_charts()
    # else:
    #     logging.info("No profile generated.")

#
# def merge():
#     profile_db = ProfileDB()
#     profile_cache = profile_db.get_cache()
#     for benchmark in BenchmarkDB.all():
#         for vendor in VendorDB.ANALYZED_VENDORS:
#             for machine in config.machines.values():
#                 profiles = profile_db.resolve_all(
#                     resolve.BY_BENCHMARK(benchmark), resolve.BY_VENDOR(vendor),
#                     resolve.BY_MACHINE(machine),
#                     resolve.VALID_PROCESSED_PROFILE(),
#                 )
#
#                 if len(profiles) > 0:
#
#                     # Check if update needed
#                     current_aggregate_profile = profile_db.resolve_most_recent(
#                         resolve.BY_AGGREGATED_BENCHMARK_AND_VENDOR(benchmark, vendor),
#                         resolve.BY_MACHINE(machine),
#                     )
#                     if current_aggregate_profile is None or any(profile.check_dependent_file_needs_update(current_aggregate_profile.file_path) for profile in profiles):
#
#                         links = [f"[{profile}]({profile.storage_base_path.relative_to(constants.MEASUREMENTS_DIR)})" for profile in profiles]
#                         logging.info(f"Merging profiles {benchmark.name} {vendor.name} {machine.id}: {str_join(links)}")
#                         aggregated_profile = AggregatedProfile.from_profiles(profiles)
#                         aggregated_profile.save()
#
#                         profile_cache.update(aggregated_profile, persist=False)
#
#     profile_cache.save()


class Command(BaseCommand):
    help = "Analyzes profiles"

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("--force", action='store_true', help="Force analysis of all profiles, even if they were already analyzed.")

    def handle(self, *args, **options):
        markdown_formatter = logging.Formatter("%(levelname)s: %(message)s\n")
        util.setup_logging(log_file=constants.MEASUREMENTS_DIR.joinpath("analysis.log.md"), log_file_mode="w",
                           log_file_formatter=markdown_formatter)

        force = options["force"]

        with util.StackTraceGuard():
            start_time = datetime.now()

            converted_profiles = analyze(force=force)
            # merge()

            completion_time = datetime.now()
            logging.info(f"Analysis of {converted_profiles} profiles completed in {completion_time - start_time}.")
