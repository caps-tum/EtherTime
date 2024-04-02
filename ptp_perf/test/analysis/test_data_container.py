from datetime import timedelta
from unittest import TestCase

import pandas as pd

from ptp_perf.profiles.data_container import Timeseries


class TestTimeseries(TestCase):
    sampleFrame = pd.DataFrame(
        {
            'clock_diff': [-0.1, 0.2, 0, 3, -4],
            'path_delay': [20, 10, 50, 42.2, 9],
        },
        index=[timedelta(seconds = 0), timedelta(seconds= 1), timedelta(seconds=2), timedelta(seconds=3), timedelta(seconds=4)]
    )
    sampleFrame.index.set_names("timestamp", inplace=True)

    def test_validate(self):
        Timeseries.from_series(TestTimeseries.sampleFrame).validate()

        # Wrong index type
        self.assertRaises(AssertionError, lambda: Timeseries.from_series(TestTimeseries.sampleFrame.reset_index()).validate())

        # Extra column
        extra_frame = TestTimeseries.sampleFrame.copy()
        extra_frame["TEST"] = 0
        self.assertRaises(AssertionError, lambda: Timeseries.from_series(extra_frame).validate())


    def test_segment(self):
        data = Timeseries.from_series(TestTimeseries.sampleFrame)

        # Basic segmentation
        segments = data.segment_and_align(
            align=pd.Series([timedelta(seconds=1.5), timedelta(seconds=3.5)])
        )

        print(segments)

        # After segmentation, we should no longer have values > 1.5
        self.assertLess(segments.time_index.max(), timedelta(seconds=1.5))

