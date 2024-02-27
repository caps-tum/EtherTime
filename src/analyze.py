import logging
from datetime import datetime

import config
import constants
import util
from profiles.aggregated_profile import AggregatedProfile
from profiles.base_profile import ProfileType
from registry import resolve
from registry.benchmark_db import BenchmarkDB
from registry.resolve import ProfileDB
from util import str_join
from vendor.registry import VendorDB


def analyze():
    profile_db = ProfileDB()
    profile_db.invalidate_cache()

    logging.info("About to remove all processed profiles.")

    # Remove all previously processed data to avoid out-of-date profiles
    old_profiles = profile_db.resolve_all(resolve.VALID_PROCESSED_PROFILE())
    old_profiles += profile_db.resolve_all(resolve.BY_TYPE(ProfileType.PROCESSED_CORRUPT))
    old_profiles += profile_db.resolve_all(resolve.BY_TYPE(ProfileType.AGGREGATED))
    logging.info(f"Removing {len(old_profiles)} processed profiles.")
    for processed_profile in old_profiles:
        processed_profile.file_path.unlink()

    for profile in profile_db.resolve_all(resolve.BY_TYPE(ProfileType.RAW)):
        try:
            logging.info(
                f"Converting {profile.file_path_relative} "
                f"([Folder]({profile.storage_base_path.relative_to(constants.MEASUREMENTS_DIR)}), "
                f"[Chart]({profile.get_chart_timeseries_path().relative_to(constants.MEASUREMENTS_DIR)}), "
                f"[Convergence Chart]({profile.get_chart_timeseries_path(convergence_included=True).relative_to(constants.MEASUREMENTS_DIR)}))"
            )
            processed = profile.vendor.convert_profile(profile)
            if processed is not None:
                processed.save()
            else:
                logging.info("No profile generated.")
        except Exception as e:
            logging.exception("Failed to convert profile!", exc_info=e)

    profile_db.invalidate_cache()


def merge():
    profile_db = ProfileDB()
    profile_db.invalidate_cache()
    for benchmark in BenchmarkDB.all():
        for vendor in VendorDB.ANALYZED_VENDORS:
            for machine in config.machines.values():
                profiles = profile_db.resolve_all(
                    resolve.BY_BENCHMARK(benchmark), resolve.BY_VENDOR(vendor),
                    resolve.BY_MACHINE(machine),
                    resolve.VALID_PROCESSED_PROFILE(),
                )

                if len(profiles) > 0:
                    links = [f"[{profile}]({profile.storage_base_path.relative_to(constants.MEASUREMENTS_DIR)})" for profile in profiles]
                    logging.info(f"Merging profiles {benchmark.name} {vendor.name} {machine.id}: {str_join(links)}")
                    aggregated_profile = AggregatedProfile.from_profiles(profiles)
                    aggregated_profile.save()
    profile_db.invalidate_cache()



if __name__ == '__main__':
    markdown_formatter = logging.Formatter("%(levelname)s: %(message)s\n")
    util.setup_logging(log_file=constants.MEASUREMENTS_DIR.joinpath("analysis.log.md"), log_file_mode="w", log_file_formatter=markdown_formatter)

    with util.StackTraceGuard():
        start_time = datetime.now()

        analyze()
        merge()

        completion_time = datetime.now()
        logging.info(f"Analysis completed in {completion_time - start_time}.")
