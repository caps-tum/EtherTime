import logging
from datetime import datetime
from pathlib import Path

import constants
import util
from config import current_configuration
from profiles.base_profile import ProfileType, BaseProfile
from profiles.data_container import MergedTimeSeries
from registry import resolve
from registry.benchmark_db import BenchmarkDB
from registry.resolve import ProfileDB
from util import str_join
from vendor.registry import VendorDB


def analyze():
    profile_db = ProfileDB()

    # Remove all previously processed data to avoid out-of-date profiles
    old_profiles = profile_db.resolve_all(resolve.VALID_PROCESSED_PROFILE())
    old_profiles += profile_db.resolve_all(resolve.BY_TYPE(ProfileType.PROCESSED_CORRUPT))
    old_profiles += profile_db.resolve_all(resolve.BY_TYPE(ProfileType.AGGREGATED))
    logging.info(f"Removing {len(old_profiles)} processed profiles.")
    for processed_profile in old_profiles:
        processed_profile.file_path.unlink()

    for profile in profile_db.resolve_all(resolve.BY_TYPE(ProfileType.RAW)):
        logging.info(f"Converting {profile.file_path_relative}")
        processed = profile.vendor.convert_profile(profile)
        if processed is not None:
            processed.save()


def merge():
    profile_db = ProfileDB()
    for benchmark in BenchmarkDB.all():
        for vendor in VendorDB.ANALYZED_VENDORS:
            for machine in current_configuration.cluster.machines:
                profiles = profile_db.resolve_all(
                    resolve.BY_BENCHMARK(benchmark), resolve.BY_VENDOR(vendor),
                    resolve.BY_MACHINE(machine),
                    resolve.VALID_PROCESSED_PROFILE(),
                )

                if len(profiles) > 0:
                    logging.info(f"Merging profiles {benchmark.name} {vendor.name} {machine.id}: {str_join(profiles)}")
                    aggregated_profile = BaseProfile(
                        id=f"aggregated",
                        benchmark=benchmark,
                        vendor_id=vendor.id,
                        profile_type=ProfileType.AGGREGATED,
                        machine_id=machine.id,
                        start_time=max([profile.start_time for profile in profiles])
                    )

                    aggregated_profile.time_series = MergedTimeSeries.merge_series(
                        [profile.time_series for profile in profiles],
                        labels=[profile.id for profile in profiles],
                        timestamp_align=True,
                    )
                    aggregated_profile.summary_statistics = aggregated_profile.time_series.summarize()

                    aggregated_profile.save()



if __name__ == '__main__':
    util.setup_logging(log_file=constants.CHARTS_DIR.joinpath("analysis_log.log"), log_file_mode="w")

    with util.StackTraceGuard():
        start_time = datetime.now()

        analyze()
        merge()

        completion_time = datetime.now()
        logging.info(f"Analysis completed in {completion_time - start_time}.")
