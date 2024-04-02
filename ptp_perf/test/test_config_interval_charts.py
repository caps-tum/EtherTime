import math
from unittest import TestCase

from ptp_perf.utilities.django_utilities import bootstrap_django_environment

bootstrap_django_environment()

from ptp_perf import constants
from ptp_perf.charts.comparison_chart import ComparisonChart
from ptp_perf.models.profile_query import ProfileQuery
from ptp_perf.profiles.base_profile import ProfileTags

CONFIG_CHART_DIRECTORY = constants.CHARTS_DIR.joinpath("config")


class TestConfigurationCharts(TestCase):
    @staticmethod
    def sync_interval_to_syncs_per_second(interval: float):
        return 1 / math.pow(2, interval)

    def test_create(self):
        profiles = ProfileQuery(
            tags=[ProfileTags.CATEGORY_CONFIGURATION, ProfileTags.CONFIGURATION_INTERVAL]
        ).run()

        if len(profiles) == 0:
            self.skipTest("Missing profiles.")

        chart = ComparisonChart("Time Sampling Interval", profiles, x_axis_label="PTP Sync & Delay Request Frequency (1/s)")
        chart.plot_median_clock_diff_and_path_delay(
            lambda profile: self.sync_interval_to_syncs_per_second(profile.benchmark.ptp_config.log_sync_interval),
        )
        chart.plot_logx(base=2)
        chart.save(CONFIG_CHART_DIRECTORY.joinpath("config_interval.png"), make_parents=True)

        chart = ComparisonChart(
            "Time Sample Interval (with 99-th Percentile)", profiles,
            x_axis_label="PTP Sync & Delay Request Frequency (1/s)", include_p99=True
        )
        chart.plot_median_clock_diff_and_path_delay(
            lambda profile: self.sync_interval_to_syncs_per_second(profile.benchmark.ptp_config.log_sync_interval),
        )
        chart.plot_logx(base=2)
        chart.save(CONFIG_CHART_DIRECTORY.joinpath("config_interval_p99.png"), make_parents=True)
