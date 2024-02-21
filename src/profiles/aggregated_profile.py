from typing import List

from profiles.base_profile import BaseProfile, ProfileType
from profiles.data_container import MergedTimeSeries
from util import unpack_one_value_or_error


class AggregatedProfile(BaseProfile):

    @staticmethod
    def from_profiles(profiles: List[BaseProfile]):
        from registry.benchmark_db import BenchmarkDB
        from vendor.registry import VendorDB

        benchmark_id = unpack_one_value_or_error(set([profile.benchmark.id for profile in profiles]), "Cannot merge profiles with multiple benchmarks.")
        vendor_id = unpack_one_value_or_error(set([profile.vendor.id for profile in profiles]), "Cannot merge profiles with multiple vendors.")
        machine_id = unpack_one_value_or_error(set([profile.machine_id for profile in profiles]), "Cannot merge profiles with multiple machines.")

        aggregated_profile = AggregatedProfile(
            id=f"aggregated",
            benchmark=BenchmarkDB.get(benchmark_id),
            vendor_id=VendorDB.get(vendor_id),
            profile_type=ProfileType.AGGREGATED,
            machine_id=machine_id,
            start_time=max([profile.start_time for profile in profiles])
        )

        aggregated_profile.time_series = MergedTimeSeries.merge_series(
            [profile.time_series for profile in profiles],
            labels=[profile.id for profile in profiles],
            timestamp_align=True,
        )
        aggregated_profile.summary_statistics = aggregated_profile.time_series.summarize()

        return aggregated_profile
