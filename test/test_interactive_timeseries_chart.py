from unittest import TestCase

from bokeh import plotting

from charts.interactive_timeseries_chart import InterativeTimeseriesChart
from registry import resolve
from registry.resolve import ProfileDB


class TestInterativeTimeseriesChart(TestCase):
    def test_create(self):
        chart = InterativeTimeseriesChart()
        profile_db = ProfileDB()
        profile = profile_db.resolve_most_recent(resolve.VALID_PROCESSED_PROFILE())
        figure = chart.create(profile)

        plotting.save(figure, profile_db.base_directory.joinpath(profile.filename.replace(".json", "-chart.html")))
