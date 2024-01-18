from dataclasses import dataclass, field, Field
from datetime import datetime, timedelta
from typing import List, ClassVar, Annotated, Tuple, Optional

import numpy as np
import pandas as pd
import pydantic
from scipy import stats
from statsmodels.tsa import stattools

import util
from profiles.base_profile import BaseProfile
from utilities import units


@dataclass
class TimeseriesValue:
    timestamp: int
    clock_offset: int


@dataclass
class TimeseriesProfile(BaseProfile):
    data: List[TimeseriesValue] = field(default_factory=list)

    COLUMN_TIMESTAMP: ClassVar[str] = "timestamp"
    COLUMN_TIMESTAMP_TIMEDELTA: ClassVar[str] = "timestamp_timedelta"
    COLUMN_CLOCK_OFFSET: ClassVar[str] = "clock_offset"
    COLUMN_CLOCK_OFFSET_ABS: ClassVar[str] = "clock_offset_abs"
    COLUMN_CLOCK_OFFSET_MOVING_AVERAGE: ClassVar[str] = "clock_offset_moving_average"
    COLUMN_PROFILE: ClassVar[str] = "profile"
    COLUMN_STATIONARY_TEST_CONFIDENCE = "stationary_test_confidence"

    def as_frame(self):
        frame = pd.DataFrame(
            self.data, columns=[TimeseriesProfile.COLUMN_TIMESTAMP, TimeseriesProfile.COLUMN_CLOCK_OFFSET]
        )

        if len(self.data) == 0:
            return frame

        frame[self.COLUMN_TIMESTAMP_TIMEDELTA] = frame[self.COLUMN_TIMESTAMP].astype("timedelta64[ns]")
        frame[self.COLUMN_TIMESTAMP] *= units.NANOSECONDS_TO_SECONDS
        frame[self.COLUMN_CLOCK_OFFSET] *= units.NANOSECONDS_TO_SECONDS
        frame[self.COLUMN_CLOCK_OFFSET_ABS] = abs(frame[self.COLUMN_CLOCK_OFFSET])

        frame[self.COLUMN_PROFILE] = self.filename

        return frame

    def add_moving_average(self, frame: pd.DataFrame, moving_average_interval: timedelta):
        frame[self.COLUMN_CLOCK_OFFSET_MOVING_AVERAGE] = self.rolling_clock_offset(
            frame, moving_average_interval, win_type='triang', column=self.COLUMN_CLOCK_OFFSET_ABS
        ).mean().reset_index(drop=True)
        # frame["clock_offset_average_interval"] = moving_average_interval.total_seconds()
        return frame

    def rolling_clock_offset(self, frame: pd.DataFrame, window_size: timedelta, win_type: str = None, column: str = COLUMN_CLOCK_OFFSET):
        return frame[column].set_axis(frame[TimeseriesProfile.COLUMN_TIMESTAMP]).rolling(
            window=int(window_size.total_seconds()),
            center=True,
            win_type=win_type,
        )

    def resampled_clock_offset(self, frame: pd.DataFrame, window_size: timedelta, win_type: str = None):
        return frame[TimeseriesProfile.COLUMN_CLOCK_OFFSET_ABS].set_axis(frame[TimeseriesProfile.COLUMN_TIMESTAMP_TIMEDELTA]).resample(
            rule=window_size,
        )

    def check_stationary(self, frame: pd.DataFrame, window: timedelta):
        if frame.empty:
            return
        # stationary_test: Tuple
        # stationary_test = stattools.adfuller(frame[TimeseriesProfile.COLUMN_CLOCK_OFFSET])
        # is_stationary = stationary_test[1] <= 0.01
        # print(
        #     util.unpack_one_value(frame[TimeseriesProfile.COLUMN_PROFILE].unique()),
        #     is_stationary, "\n",
        #     stationary_test,
        # )

        # frame[self.COLUMN_STATIONARY_TEST_CONFIDENCE] = self.resampled_clock_offset(frame, window).apply(
        #     lambda window_values: stattools.adfuller(frame[TimeseriesProfile.COLUMN_CLOCK_OFFSET])[1]
        # ).reset_index(drop=True)
        # self.rolling_clock_offset(window).apply(
        #     lambda values: stattools.adfuller(values)
        # )

        # def do_correlation(window_values: pd.Series, ):
        #     min_timestamp = window_values.index.min()
        #     # Split timestamps by half interval
        #     # The data we get is half the window width
        #     split_timestamp = min_timestamp + window.total_seconds() / 4
        #     first_half = window_values[:split_timestamp]
        #     second_half = window_values[split_timestamp:]
        #
        #     means = first_half.mean(), second_half.mean()
        #     stds = first_half.std(), second_half.std()
        #
        #     # return abs(means[0] - means[1]) / (0.5 * (abs(means[0]) + abs(means[1]))) + \
        #     #     abs(stds[0] - stds[1]) / (0.5 * (abs(stds[0]) + abs(stds[1])))
        #     # return abs(means[0] - means[1]) / (1 * (abs(means[0]) + abs(means[1])))
        #     return abs(means[0] - means[1]) / window_values.std()
        #     # return abs(stds[0] - stds[1]) / (0.5 * (abs(stds[0]) + abs(stds[1])))
        #
        # diffs = self.resampled_clock_offset(frame, window).mean().diff().abs()
        # diffs.index.astype('int64', copy=False)
        # frame[self.COLUMN_STATIONARY_TEST_CONFIDENCE] = diffs.reindex(
        #     frame[self.COLUMN_TIMESTAMP].astype("timedelta64[s]"), method='nearest'
        # ).reset_index(drop=True)



        # Pearson correlation
        # frame[self.COLUMN_STATIONARY_TEST_CONFIDENCE] = self.rolling_clock_offset(
        #     frame, window,
        # ).apply(
        #     lambda x: do_correlation(x),
        # ).reset_index(drop=True)

        # Welch's t-test unequal variances
        previous_window: Optional[pd.Series] = None
        def do_correlation(window_values: pd.Series):
            nonlocal previous_window
            if previous_window is None:
                previous_window = window_values
                return np.nan

            pvalue = stats.ttest_ind(previous_window, window_values, equal_var=False, ).pvalue
            previous_window = window_values

            return pvalue

        # diffs = self.rolling_clock_offset(frame, window).apply(do_correlation)
        # frame[self.COLUMN_STATIONARY_TEST_CONFIDENCE] = diffs.reset_index(drop=True)
        # diffs = self.resampled_clock_offset(frame, window).apply(do_correlation)
        # frame[self.COLUMN_STATIONARY_TEST_CONFIDENCE] = self.time_reindex_nearest_neighbor(diffs, frame)

        def overlap(min1, max1, min2, max2):
            return np.maximum(0, np.minimum(max1, max2) - np.maximum(min1, min2))

        def do_bootstrap(values: pd.Series):
            bootstrap_result = stats.bootstrap(
                (values, ), statistic=np.mean,
                confidence_level=0.99,
                random_state=1,
            )
            # return pd.Series(
            #     [np.mean(values), bootstrap_result.confidence_interval.low, bootstrap_result.confidence_interval.high],
            #     index=["mean", "confidence_interval_low", "confidence_interval_high"],
            # )
            # return pd.DataFrame([{
            #     "mean": np.mean(values),
            #     "confidence_interval_low": bootstrap_result.confidence_interval.low,
            #     "confidence_interval_high": bootstrap_result.confidence_interval.high,
            # }])
            return bootstrap_result.confidence_interval.low, bootstrap_result.confidence_interval.high

        bootstrap_result = self.resampled_clock_offset(frame, window).agg({
            'clock_offset_mean': "mean",
            'clock_offset_mean_confidence_low': lambda x: x.quantile(0.0),
            'clock_offset_mean_confidence_high': lambda x: x.quantile(1.0),
        })

        bootstrap_result[self.COLUMN_STATIONARY_TEST_CONFIDENCE] = overlap(
            bootstrap_result['clock_offset_mean_confidence_low'].shift(1),
            bootstrap_result['clock_offset_mean_confidence_high'].shift(1),
            bootstrap_result['clock_offset_mean_confidence_low'],
            bootstrap_result['clock_offset_mean_confidence_high']
        )

        frame = pd.concat(
            [frame, self.time_reindex_nearest_neighbor(frame, bootstrap_result)],
            axis="columns",
        )

        return frame

    def time_reindex_nearest_neighbor(self, target_frame, values):
        values.index.astype('int64', copy=False)
        return values.reindex(
            target_frame[self.COLUMN_TIMESTAMP].astype("timedelta64[s]"), method='nearest'
        ).reset_index(drop=True)
