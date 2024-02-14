import math
from unittest import TestCase

import constants
from charts.comparison_chart import ComparisonChart
from profiles.base_profile import ProfileTags
from registry import resolve
from registry.resolve import ProfileDB

CONFIG_CHART_DIRECTORY = constants.CHARTS_DIR.joinpath("config")


class TestConfigurationCharts(TestCase):
    @staticmethod
    def sync_interval_to_syncs_per_second(interval: float):
        return 1 / math.pow(2, interval)

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
            lambda profile: self.sync_interval_to_syncs_per_second(profile.benchmark.ptp_config.log_sync_interval),
            x_axis_label="PTP Sync & Delay Request Frequency (1/s)",
        )
        chart.plot_logx(base=2)
        chart.save(CONFIG_CHART_DIRECTORY.joinpath("config_interval.png"), make_parent=True)

        chart = ComparisonChart("Time Sample Interval (with 99-th Percentile)", profiles, nrows=2)
        chart.plot_median_clock_diff_and_path_delay(
            lambda profile: self.sync_interval_to_syncs_per_second(profile.benchmark.ptp_config.log_sync_interval),
            x_axis_label="PTP Sync & Delay Request Frequency (1/s)",
            include_p99=True,
        )
        chart.plot_logx(base=2)
        chart.save(CONFIG_CHART_DIRECTORY.joinpath("config_interval_p99.png"), make_parent=True)
