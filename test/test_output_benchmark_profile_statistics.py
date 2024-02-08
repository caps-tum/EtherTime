
from unittest import TestCase

import pandas as pd
from bokeh import plotting

from charts.interactive_timeseries_chart import InteractiveTimeseriesChart
from constants import CHARTS_DIR
from registry import resolve
from registry.benchmark_db import BenchmarkDB
from registry.resolve import ProfileDB
from utilities import units


class TestOutputBenchmarkProfileStatistics(TestCase):
    def test_output(self):
        profile_db = ProfileDB()
        profiles = profile_db.resolve_all(resolve.VALID_PROCESSED_PROFILE())

        records = {benchmark.id: 0 for benchmark in BenchmarkDB.all()}

        for profile in profiles:
            records[profile.benchmark.id] += 1

        for id, count in records.items():
            print(f'{id}: {count}')
