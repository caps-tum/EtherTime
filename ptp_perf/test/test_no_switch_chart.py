from unittest import TestCase

from ptp_perf import constants
from charts.timeseries_chart_versus import TimeSeriesChartVersus
from registry import resolve
from registry.benchmark_db import BenchmarkDB

CHART_DIRECTORY = constants.CHARTS_DIR.joinpath("no_switch")
from registry.resolve import ProfileDB
from ptp_perf.vendor.registry import VendorDB


class Test1To2Charts(TestCase):
    profile_db = ProfileDB()

    def test_no_switch_chart(self):
        for vendor in VendorDB.ANALYZED_VENDORS:
            baseline = self.profile_db.resolve_most_recent(
                resolve.BY_VALID_BENCHMARK_AND_VENDOR(BenchmarkDB.BASE, vendor)
            )
            no_switch = self.profile_db.resolve_most_recent(
                resolve.BY_VALID_BENCHMARK_AND_VENDOR(BenchmarkDB.NO_SWITCH, vendor)
            )
            if baseline is None or no_switch is None:
                continue

            chart = TimeSeriesChartVersus(baseline, no_switch, include_path_delay=True)
            chart.save(CHART_DIRECTORY.joinpath(f"base_vs_no_switch_{vendor}.png"), make_parent=True)
