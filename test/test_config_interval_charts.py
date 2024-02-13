from unittest import TestCase

import constants
from charts.comparison_chart import ComparisonChart
from profiles.base_profile import ProfileTags
from registry import resolve
from registry.resolve import ProfileDB

CONFIG_CHART_DIRECTORY = constants.CHARTS_DIR.joinpath("config")


class TestLoadCharts(TestCase):
    def test_create(self):
        profile_db = ProfileDB()
        profiles = profile_db.resolve_all(
            resolve.VALID_PROCESSED_PROFILE(),
            resolve.BY_TAGS(
                ProfileTags.CATEGORY_CONFIGURATION, ProfileTags.CONFIGURATION_INTERVAL,
            )
        )

        chart = ComparisonChart("Time Sampling Interval", profiles, nrows=2)
        chart.plot_median_clock_diff_and_path_delay(
            lambda profile: profile.benchmark.ptp_config.log_sync_interval,
            x_axis_label="PTP Sync & Delay Request Interval (log scale)",
        )
        chart.save(CONFIG_CHART_DIRECTORY.joinpath("config_interval.png"), make_parent=True)

        chart = ComparisonChart("Unisolated Network Load", profiles, nrows=2)
        chart.plot_median_clock_diff_and_path_delay(
            lambda profile: profile.benchmark.ptp_config.log_sync_interval,
            x_axis_label="PTP Sync & Delay Request Interval (log scale)",
            include_p99=True,
        )
        chart.save(CONFIG_CHART_DIRECTORY.joinpath("config_interval_p99.png"), make_parent=True)
