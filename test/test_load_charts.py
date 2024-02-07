from unittest import TestCase

from matplotlib.ticker import PercentFormatter

import constants
from charts.comparison_chart import ComparisonChart, ComparisonDataPoint
from profiles.base_profile import ProfileTags
from registry import resolve
from registry.benchmark_db import BenchmarkDB
from registry.resolve import ProfileDB


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

        chart = ComparisonChart(
            "Unisolated Network Load",
            profiles
        )

        chart.plot_statistic(
            lambda profile: ComparisonDataPoint(
                x=profile.benchmark.artificial_load_network / 10, # GBit/s to %
                y=profile.summary_statistics.clock_diff_median,
                hue=profile.vendor.name,
            ),
            x_axis_label="Network Utilization",
            hue_name="Vendor",
        )
        chart.axes.set_yscale('log')
        chart.axes.xaxis.set_major_formatter(PercentFormatter())

        chart.save(constants.CHARTS_DIR.joinpath("load").joinpath("network_unisolated.png"), make_parent=True)
