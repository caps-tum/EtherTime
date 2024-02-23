
from unittest import TestCase

import pandas as pd
from natsort import natsorted, natsort_keygen
from registry import resolve
from registry.resolve import ProfileDB


class TestOutputBenchmarkProfileStatistics(TestCase):
    def test_output(self):
        profile_db = ProfileDB()
        profiles = profile_db.resolve_all(resolve.VALID_PROCESSED_PROFILE())

        records = [{
            "Benchmark": profile.benchmark.name,
            "Vendor": profile.vendor.name,
            "Profile": profile.id,
        } for profile in profiles]

        frame = pd.DataFrame(records)

        benchmarks_by_vendor = frame.groupby(by=["Benchmark", "Vendor"]).count().unstack("Vendor")
        # Discard one level of multiindex
        # benchmarks_by_vendor.columns = benchmarks_by_vendor.columns.to_flat_index()
        benchmarks_by_vendor.columns = benchmarks_by_vendor.columns.get_level_values(-1)
        benchmarks_by_vendor = benchmarks_by_vendor.rename_axis(None, axis=1).reset_index().sort_values(by="Benchmark", key=natsort_keygen()).reset_index(drop=True)
        print(benchmarks_by_vendor)
        # Avoid overlap with stderr
        print("")
