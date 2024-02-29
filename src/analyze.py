import logging
from datetime import datetime

import config
import constants
import util
from profiles.aggregated_profile import AggregatedProfile
from profiles.base_profile import ProfileType, BaseProfile
from registry import resolve
from registry.benchmark_db import BenchmarkDB
from registry.resolve import ProfileDB
from util import str_join
from vendor.registry import VendorDB


def analyze():
    profile_db = ProfileDB()

    logging.info("Updating profile cache...")
    start_time = datetime.now()
    profile_db.update_cache()
    logging.info(f"Updated profile cache in {datetime.now() - start_time}.")

    for profile in profile_db.resolve_all(resolve.BY_TYPE(ProfileType.RAW)):
        try:
            if profile.check_dependent_file_needs_update(profile.get_file_path(ProfileType.PROCESSED, profile.machine_id)):
                convert_profile(profile, profile_db)
        except Exception as e:
            logging.exception("Failed to convert profile!", exc_info=e)


def convert_profile(profile: BaseProfile, profile_db: ProfileDB = None):
    if profile_db is None:
        profile_db = ProfileDB()

    logging.info(
        f"Converting {profile.file_path_relative} "
        f"([Folder]({profile.storage_base_path.relative_to(constants.MEASUREMENTS_DIR)}), "
        f"[Chart]({profile.get_chart_timeseries_path().relative_to(constants.MEASUREMENTS_DIR)}), "
        f"[Convergence Chart]({profile.get_chart_timeseries_path(convergence_included=True).relative_to(constants.MEASUREMENTS_DIR)}))"
    )
    processed_profile = profile.vendor.convert_profile(profile)
    if processed_profile is not None:
        # Remove existing processed profiles (they may be in a different path)
        processed_profile.get_file_path(ProfileType.PROCESSED).unlink(missing_ok=True)
        processed_profile.get_file_path(ProfileType.PROCESSED_CORRUPT).unlink(missing_ok=True)

        processed_profile.save()
        profile_db.get_cache().update(processed_profile)

        processed_profile.create_timeseries_charts()
    else:
        logging.info("No profile generated.")


def merge():
    profile_db = ProfileDB()
    profile_cache = profile_db.get_cache()
    for benchmark in BenchmarkDB.all():
        for vendor in VendorDB.ANALYZED_VENDORS:
            for machine in config.machines.values():
                profiles = profile_db.resolve_all(
                    resolve.BY_BENCHMARK(benchmark), resolve.BY_VENDOR(vendor),
                    resolve.BY_MACHINE(machine),
                    resolve.VALID_PROCESSED_PROFILE(),
                )

                if len(profiles) > 0:

                    # Check if update needed
                    current_aggregate_profile = profile_db.resolve_most_recent(
                        resolve.BY_AGGREGATED_BENCHMARK_AND_VENDOR(benchmark, vendor),
                        resolve.BY_MACHINE(machine),
                    )
                    if current_aggregate_profile is None or any(profile.check_dependent_file_needs_update(current_aggregate_profile.file_path) for profile in profiles):

                        links = [f"[{profile}]({profile.storage_base_path.relative_to(constants.MEASUREMENTS_DIR)})" for profile in profiles]
                        logging.info(f"Merging profiles {benchmark.name} {vendor.name} {machine.id}: {str_join(links)}")
                        aggregated_profile = AggregatedProfile.from_profiles(profiles)
                        aggregated_profile.save()

                        profile_cache.update(aggregated_profile, persist=False)

    profile_cache.save()



if __name__ == '__main__':
    markdown_formatter = logging.Formatter("%(levelname)s: %(message)s\n")
    util.setup_logging(log_file=constants.MEASUREMENTS_DIR.joinpath("analysis.log.md"), log_file_mode="w", log_file_formatter=markdown_formatter)

    with util.StackTraceGuard():
        start_time = datetime.now()

        analyze()
        merge()

        completion_time = datetime.now()
        logging.info(f"Analysis completed in {completion_time - start_time}.")
