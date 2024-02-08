from unittest import TestCase

import config
import constants

CHART_DIRECTORY = constants.CHARTS_DIR.joinpath("1_to_2")
from charts.timeseries_chart_comparison import TimeSeriesChartComparison
from registry import resolve
from registry.benchmark_db import BenchmarkDB
from registry.resolve import ProfileDB
from vendor.registry import VendorDB


class Test1To2Charts(TestCase):

    def test_1_to_2_charts(self):
        vendors = [VendorDB.PTPD.id, VendorDB.LINUXPTP.id]
        profile_db = ProfileDB()

        # Compare base, and the 2 1-to-2-clients
        for vendor_id in vendors:
            chart = TimeSeriesChartComparison([
                profile_db.resolve_most_recent(
                    resolve.VALID_PROCESSED_PROFILE(), resolve.BY_BENCHMARK(BenchmarkDB.BASE),
                    resolve.BY_VENDOR(VendorDB.get(vendor_id))
                ),
                profile_db.resolve_most_recent(
                    resolve.VALID_PROCESSED_PROFILE(),
                    resolve.BY_BENCHMARK(BenchmarkDB.BASE_TWO_CLIENTS),
                    resolve.BY_MACHINE(config.MACHINE_RPI08),
                    resolve.BY_VENDOR(VendorDB.get(vendor_id)),
                ),
                profile_db.resolve_most_recent(
                    resolve.VALID_PROCESSED_PROFILE(),
                    resolve.BY_BENCHMARK(BenchmarkDB.BASE_TWO_CLIENTS),
                    resolve.BY_MACHINE(config.MACHINE_RPI07),
                    resolve.BY_VENDOR(VendorDB.get(vendor_id)),
                ),
            ], labels=["Baseline", "1-to-2 Client 1", "1-to-2 Client 2"], x_label="Profile")

            chart.save(CHART_DIRECTORY.joinpath(f"1_to_2_clients_versus_base_{vendor_id}.png"), make_parent=True)
