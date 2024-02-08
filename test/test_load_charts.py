from unittest import TestCase

from matplotlib.ticker import PercentFormatter

import config
import constants

LOAD_CHART_DIRECTORY = constants.CHARTS_DIR.joinpath("load")
from charts.comparison_chart import ComparisonChart, ComparisonDataPoint
from charts.timeseries_chart_comparison import TimeSeriesChartComparison
from charts.timeseries_chart_versus import TimeSeriesChartVersus
from profiles.base_profile import ProfileTags
from registry import resolve
from registry.benchmark_db import BenchmarkDB, NetworkContentionType
from registry.resolve import ProfileDB, VALID_PROCESSED_PROFILE
from vendor.registry import VendorDB


class TestLoadCharts(TestCase):
    def test_create(self):
        profile_db = ProfileDB()
        profiles = profile_db.resolve_all(
            resolve.VALID_PROCESSED_PROFILE(),
            resolve.BY_TAGS(
                ProfileTags.CATEGORY_LOAD, ProfileTags.COMPONENT_NET, ProfileTags.ISOLATION_UNPRIORITIZED,
            )
        )
        # Also include the baseline
        profiles += profile_db.resolve_all(
            resolve.VALID_PROCESSED_PROFILE(),
            resolve.BY_BENCHMARK(BenchmarkDB.BASE),
        )

        profiles.sort(key=lambda profile: profile.benchmark.artificial_load_network)

        chart = ComparisonChart(
            "Unisolated Network Load",
            profiles,
            nrows=2,
        )

        chart.plot_statistic(lambda profile: ComparisonDataPoint(
            x=profile.benchmark.artificial_load_network / 10,  # GBit/s to %
            y=profile.summary_statistics.clock_diff_median,
            hue=profile.vendor.name,
        ), x_axis_label="Network Utilization", hue_name="Vendor")
        # chart.current_axes.set_yscale('log')
        chart.current_axes.xaxis.set_major_formatter(PercentFormatter())

        chart.set_current_axes(1, 0)
        chart.plot_statistic(lambda profile: ComparisonDataPoint(
            x=profile.benchmark.artificial_load_network / 10,  # GBit/s to %
            y=profile.summary_statistics.path_delay_median,
            hue=profile.vendor.name,
        ), x_axis_label="Network Utilization", hue_name="Vendor")
        chart.current_axes.xaxis.set_major_formatter(PercentFormatter())
        chart.current_axes.set_ylabel('Path Delay')

        chart.save(LOAD_CHART_DIRECTORY.joinpath("load_network_unisolated.png"), make_parent=True)

        chart.set_current_axes(0, 0)
        chart.plot_statistic(
            lambda profile: ComparisonDataPoint(
                x=profile.benchmark.artificial_load_network / 10,  # GBit/s to %
                y=profile.summary_statistics.clock_diff_p99,
                hue=f"{profile.vendor.name} P_{{99}}",
            ),
            x_axis_label="Network Utilization",
            hue_name="Vendor",
            linestyle='dotted',
        )

        chart.save(LOAD_CHART_DIRECTORY.joinpath("load_network_unisolated_p99.png"), make_parent=True)

        # Show some distribution trends for each vendor
        vendors = set(profile.vendor.id for profile in profiles)
        for vendor_id in vendors:
            filtered_profiles = [profile for profile in profiles if profile.vendor.id == vendor_id]
            # Distribution chart
            chart = TimeSeriesChartComparison(
                filtered_profiles,
                labels=[f"{profile.benchmark.artificial_load_network / 10:.0f}%" for profile in filtered_profiles],
                x_label="Network Load",
            )
            # chart.axes.set_yscale('log')
            chart.save(LOAD_CHART_DIRECTORY.joinpath(f"load_network_unisolated_distributions_{vendor_id}.png"), make_parent=True)

        # Compare unisolated to isolated
        for vendor_id in vendors:
            chart = TimeSeriesChartVersus(
                profile_db.resolve_most_recent(
                    resolve.VALID_PROCESSED_PROFILE(),
                    resolve.BY_BENCHMARK(BenchmarkDB.BASE),
                    resolve.BY_VENDOR(VendorDB.get(vendor_id))
                ),
                profile_db.resolve_most_recent(
                    resolve.VALID_PROCESSED_PROFILE(),
                    resolve.BY_BENCHMARK(BenchmarkDB.network_contention(NetworkContentionType.UNPRIORITIZED, 100)),
                    resolve.BY_VENDOR(VendorDB.get(vendor_id)),
                )
            )
            chart.save(LOAD_CHART_DIRECTORY.joinpath(f"load_network_unisolated_versus_{vendor_id}.png"))

        # Compare base, unisolated, prioritized, (eventually isolated)
        for vendor_id in vendors:
            chart = TimeSeriesChartComparison([
                profile_db.resolve_most_recent(
                    resolve.VALID_PROCESSED_PROFILE(), resolve.BY_BENCHMARK(BenchmarkDB.BASE),
                    resolve.BY_VENDOR(VendorDB.get(vendor_id))
                ),
                profile_db.resolve_most_recent(
                    resolve.VALID_PROCESSED_PROFILE(),
                    resolve.BY_BENCHMARK(BenchmarkDB.network_contention(NetworkContentionType.UNPRIORITIZED, 100)),
                    resolve.BY_VENDOR(VendorDB.get(vendor_id)),
                ),
                profile_db.resolve_most_recent(
                    resolve.VALID_PROCESSED_PROFILE(),
                    resolve.BY_BENCHMARK(BenchmarkDB.network_contention(NetworkContentionType.PRIORITIZED, 100)),
                    resolve.BY_VENDOR(VendorDB.get(vendor_id)),
                ),
            ], labels=["Baseline", "Unprioritized (100% load)", "Prioritized (100% load)"], x_label="Profile")

            chart.save(LOAD_CHART_DIRECTORY.joinpath(f"load_network_versus_base_{vendor_id}.png"))
