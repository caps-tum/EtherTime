from unittest import TestCase

import pandas as pd
from bokeh import plotting

from charts.interactive_timeseries_chart import InterativeTimeseriesChart
from constants import CHARTS_DIR
from registry import resolve
from registry.resolve import ProfileDB
from utilities import units


class TestOutputCSV(TestCase):
    def test_create(self):
        profile_db = ProfileDB()
        profiles = profile_db.resolve_all(resolve.VALID_PROCESSED_PROFILE())

        records = []

        for profile in profiles:
            record = {
                'Benchmark': profile.benchmark.name,
                'Vendor': profile.vendor.name,
                'Date': profile.start_time.replace(second=0, microsecond=0),
                **profile.summary_statistics.export(units.MICROSECONDS_IN_SECOND),
                **profile.convergence_statistics.export(units.MICROSECONDS_IN_SECOND),
            }
            records.append(record)

        pd.DataFrame(records).to_csv(CHARTS_DIR.joinpath("profiles.csv"), index=False)
