from unittest import TestCase

import bokeh.util.serialization
from bokeh import plotting

from charts.interactive_timeseries_chart import InterativeTimeseriesChart
from registry import resolve
from registry.resolve import ProfileDB


class TestInterativeTimeseriesChart(TestCase):
    def test_create(self):
        # Patch bokeh to generate predictable UUIDS
        bokeh.util.serialization.make_globally_unique_id = bokeh.util.serialization.make_id

        chart = InterativeTimeseriesChart()
        profile_db = ProfileDB()
        profiles = profile_db.resolve_all(resolve.VALID_PROCESSED_PROFILE())
        for profile in profiles:
            figure = chart.create(profile)
            plotting.save(
                figure,
                filename=profile_db.base_directory.joinpath(profile.filename.replace(".json", "-chart.html")),
                resources="cdn",
                title=f"{profile.id}",
            )
