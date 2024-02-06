from unittest import TestCase

import pandas as pd
from bokeh import plotting

import constants
from charts.comparison_chart import ComparisonChart
from charts.interactive_timeseries_chart import InterativeTimeseriesChart
from constants import CHARTS_DIR
from profiles.base_profile import ProfileTags
from registry import resolve
from registry.resolve import ProfileDB
from utilities import units


class TestOutputCSV(TestCase):
    def test_create(self):
        profile_db = ProfileDB()
        profiles = profile_db.resolve_all(
            resolve.VALID_PROCESSED_PROFILE(),
            resolve.BY_TAGS(
                ProfileTags.CATEGORY_LOAD, ProfileTags.COMPONENT_NET, ProfileTags.ISOLATION_UNPRIORITIZED,
            )
        )

        chart = ComparisonChart(
            "Unisolated Network Load",
            profiles
        )

        chart.plot_statistic(lambda profile: (profile.benchmark.artificial_load_network, profile.summary_statistics.clock_diff_median))

        chart.save(constants.CHARTS_DIR.joinpath("load").joinpath("network_unisolated.png"), make_parent=True)
