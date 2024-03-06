import hashlib
import io
import logging
import math
import typing
from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable, Any, Optional, Dict, List

import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd
from pandas.core.dtypes.common import is_numeric_dtype, is_timedelta64_ns_dtype
from pandas.core.dtypes.inference import is_number

from ptp_perf.profiles.data_cache import SummaryStatisticCache
from ptp_perf.util import unpack_one_value, TimerUtil

if typing.TYPE_CHECKING:
    from ptp_perf.profiles.analysis import DetectedClockConvergence

ANNOTATION_BBOX_PROPS = dict(boxstyle='round', facecolor=(1.0, 1.0, 1.0, 0.85), edgecolor=(0.6, 0.6, 0.6, 1.0))


@dataclass
class BootstrapMetric:
    value: float
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None

    def format(self):
        formatter = None
        for places in range(6):
            formatter = matplotlib.ticker.EngFormatter(unit="s", places=places, usetex=False)

            if self.confidence_interval_lower is None or math.isnan(self.confidence_interval_lower) or self.confidence_interval_upper is None or math.isnan(self.confidence_interval_upper):
                return f"{formatter.format_data(self.value)}?"

            lower_bound = formatter.format_data(self.confidence_interval_lower)
            upper_bound = formatter.format_data(self.confidence_interval_upper)

            if lower_bound != upper_bound:
                return f"[{lower_bound} - {upper_bound}]"

        return formatter.format_data(self.value)

    @staticmethod
    def create(data: pd.Series, quantile: float):
        import scipy
        bootstrap_result = scipy.stats.bootstrap(
            # Samples must be in a sequence, this isn't clear from the documentation
            # https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html
            (data,),
            lambda sample, axis: np.quantile(sample, quantile, axis=axis),
            random_state=np.random.default_rng(0), vectorized=True,
            # Try to stay within 10M values processed per batch to limit memory consumption
            batch=max(10 * (1024 ** 2) // len(data), 1),
            # method='basic',
        )
        return BootstrapMetric(
            value=data.quantile(quantile),
            confidence_interval_lower=bootstrap_result.confidence_interval.low,
            confidence_interval_upper=bootstrap_result.confidence_interval.high
        )

    @property
    def relative_magnitude(self) -> float:
        return abs((self.confidence_interval_upper - self.confidence_interval_lower) / self.value)


@dataclass
class SummaryStatistics:
    clock_diff_median: BootstrapMetric = None
    clock_diff_p99: BootstrapMetric = None
    path_delay_median: BootstrapMetric = None

    def plot_annotate(self, ax: plt.Axes):
        ax.annotate(
            f"Median: {self.clock_diff_median.format()}\n"
            f"$P_{{99}}$: {self.clock_diff_p99.format()}\n"
            f"Path Delay: {self.path_delay_median.format()}",
            xy=(0.95, 0.95), xycoords='axes fraction',
            verticalalignment='top', horizontalalignment='right',
            bbox=ANNOTATION_BBOX_PROPS,
        )

    def export(self, unit_multiplier: int = 1) -> Dict:
        return {
            'Clock Difference (Median)': self.clock_diff_median.value * unit_multiplier,
            'Clock Difference (99-th Percentile)': self.clock_diff_p99.value * unit_multiplier,
            'Path Delay (Median)': self.path_delay_median.value * unit_multiplier,
        }


@dataclass
class ConvergenceStatistics:
    convergence_time: timedelta
    convergence_max_offset: float
    convergence_rate: float

    def plot_annotate(self, ax: plt.Axes):
        import matplotlib.ticker
        formatter = matplotlib.ticker.EngFormatter(unit="s", places=0, usetex=True)
        rate_formatter = matplotlib.ticker.EngFormatter(unit="s/s", places=0, usetex=True)

        # Just discard microseconds for display
        display_convergence_time = self.convergence_time - timedelta(microseconds=self.convergence_time.microseconds)

        ax.annotate(
            f"Convergence Time: {display_convergence_time}\n"
            f"Initial Step Error: {formatter.format_data(self.convergence_max_offset)}\n"
            f"Convergence Rate: {rate_formatter.format_data(self.convergence_rate)}",
            xy=(0.95, 0.95), xycoords='axes fraction',
            verticalalignment='top', horizontalalignment='right',
            bbox=ANNOTATION_BBOX_PROPS,
        )

    @staticmethod
    def from_convergence_series(detected_clock_convergence: "DetectedClockConvergence",
                                convergence_series: pd.Series) -> Optional["ConvergenceStatistics"]:
        convergence_max_offset = convergence_series.abs().max()
        if math.isnan(convergence_max_offset):
            logging.warning("No convergence data on profile, cannot calculate convergence statistics.")
            return None

        if detected_clock_convergence.duration.total_seconds() == 0:
            raise RuntimeError("Invalid detected clock convergence of 0 seconds.")

        return ConvergenceStatistics(
            convergence_time=detected_clock_convergence.duration,
            convergence_max_offset=convergence_max_offset,
            convergence_rate=convergence_max_offset / detected_clock_convergence.duration.total_seconds()
        )

    def export(self, unit_multiplier: int = 1) -> Dict:
        return {
            'Convergence Time': self.convergence_time.total_seconds(),
            'Convergence Max Offset': self.convergence_max_offset * unit_multiplier,
            'Convergence Rate': self.convergence_rate * unit_multiplier,
        }


COLUMN_TIMESTAMP_INDEX = "timestamp"
COLUMN_CLOCK_DIFF = "clock_diff"
COLUMN_PATH_DELAY = "path_delay"
COLUMN_SOURCE = "source"

def non_timestamp_index(df: pd.DataFrame) -> List[str]:
    return [name for name in df.index.names if name != COLUMN_TIMESTAMP_INDEX]


@dataclass
class Timeseries:
    data: str
    # This field doesn't have a type annotation so that pydantic will not pick it up.
    _data_frame = None

    @property
    def data_frame(self):
        if self._data_frame is None:
            read_frame = pd.read_json(io.StringIO(self.data), convert_dates=True, orient='table')
            Timeseries.convert_data_frame_index_type(
                read_frame, COLUMN_TIMESTAMP_INDEX, "timedelta64[ns]",
            )
            self.validate(read_frame)

            self._data_frame = read_frame
        return self._data_frame

    @property
    def time_index(self) -> pd.TimedeltaIndex:
        return self.data_frame.index.get_level_values(COLUMN_TIMESTAMP_INDEX)

    @property
    def clock_diff(self) -> pd.Series:
        return self.data_frame[COLUMN_CLOCK_DIFF]

    @property
    def path_delay(self) -> pd.Series:
        return self.data_frame[COLUMN_PATH_DELAY]

    def get_clock_diff(self, abs: bool) -> pd.Series:
        return self.clock_diff.abs() if abs else self.clock_diff

    def get_discriminator(self):
        return self.data_frame[COLUMN_SOURCE]

    @classmethod
    def from_series(cls, frame: pd.DataFrame):
        return cls(cls._serialize_frame(frame))

    @staticmethod
    def _serialize_frame(result_frame):
        serialization_frame: pd.DataFrame = result_frame.copy()
        Timeseries._validate_frame(result_frame)

        # Convert index type cause pandas cannot read iso timedeltas.
        Timeseries.convert_data_frame_index_type(serialization_frame, COLUMN_TIMESTAMP_INDEX, "int64")
        assert serialization_frame.index.is_unique
        return serialization_frame.to_json(
            orient="table", date_unit='ns',
        )

    @staticmethod
    def convert_data_frame_index_type(frame: pd.DataFrame, level: str, type: str):
        # We need to differentiate between single level and multi level index
        if frame.index.nlevels > 1:
            assert frame.index.levels[-1].name == COLUMN_TIMESTAMP_INDEX
            frame.index = frame.index.set_levels(
                frame.index.levels[-1].astype(type),
                level=level,
            )
        else:
            frame.set_index(
                frame.index.astype(type),
                inplace=True,
            )

    def validate(self, data_frame: pd.DataFrame = None, maximum_allowable_time_jump: timedelta = timedelta(seconds=5)):
        if data_frame is None:
            data_frame = self.data_frame

        self._validate_frame(data_frame, maximum_allowable_time_jump)

    @staticmethod
    def _validate_frame(data_frame, maximum_allowable_time_jump: timedelta = timedelta(seconds=5)):
        # Validate shape of frame and properties
        for column in [COLUMN_CLOCK_DIFF, COLUMN_PATH_DELAY]:
            assert is_numeric_dtype(data_frame[column])
        num_cols = 3 if COLUMN_SOURCE in data_frame.columns else 2
        assert num_cols == len(data_frame.columns), f"Unexpected columns in frame:\n{data_frame}"
        assert data_frame.index.is_unique, f"Frame index is not unique:\n{data_frame}"
        assert COLUMN_TIMESTAMP_INDEX in data_frame.index.names, f"Frame index does not have a timestamp level\n{data_frame}"
        assert str(data_frame.index.get_level_values(COLUMN_TIMESTAMP_INDEX).dtype) == 'timedelta64[ns]', f"Frame index level timestamps is not a series of timedeltas.\n{data_frame}"

        for label, group in Timeseries.groupby_individual_timeseries(data_frame):
            index_time_deltas = group.index.get_level_values(COLUMN_TIMESTAMP_INDEX).diff()

            # Ensure that data is sorted chronologically.
            min_time_jump = index_time_deltas.min()
            if min_time_jump < timedelta(seconds=0):
                raise RuntimeError(
                    f"Timeseries index is not monotonically increasing (minimum time difference is {min_time_jump}."
                )
            # Make sure there are no gaps in the data
            time_jumps = index_time_deltas[index_time_deltas >= maximum_allowable_time_jump]
            if not time_jumps.empty:
                logging.warning(f"Timeseries contains {len(time_jumps)} holes "
                                f"(largest hole: {time_jumps.max()}, "
                                f"total: {time_jumps.sum()} = {100 * time_jumps.sum() / index_time_deltas.sum():.0f}%)")
            # Ensure we have sufficient data in general
            # At least 10 minutes -> At least 600 samples
            if len(group) < 600:
                logging.warning(f"Timeseries contains too few data points: {len(data_frame)}")

    @staticmethod
    def _validate_series(series: pd.Series, maximum_allowable_time_jump: timedelta = timedelta(seconds=5)):
        # Validate shape of frame and properties
        assert is_numeric_dtype(series)
        assert series.index.is_unique, f"Series index is not unique:\n{series}"
        assert COLUMN_TIMESTAMP_INDEX in series.index.names, f"Series index does not have a timestamp level\n{series}"
        # Datetime64 with timezone is not so easy to detect.
        assert isinstance(series.index.get_level_values(COLUMN_TIMESTAMP_INDEX).dtype, pd.DatetimeTZDtype), f"Series index level timestamps is not a series of datetime64+tz.\n{series}"

        index_time_deltas = series.index.diff()

        # Ensure that data is sorted chronologically.
        min_time_jump = index_time_deltas.min()
        if min_time_jump < timedelta(seconds=0):
            raise RuntimeError(
                f"Timeseries index is not monotonically increasing (minimum time difference is {min_time_jump}."
            )
        # Make sure there are no gaps in the data
        time_jumps = index_time_deltas[index_time_deltas >= maximum_allowable_time_jump]
        if not time_jumps.empty:
            logging.warning(f"Timeseries contains {len(time_jumps)} holes "
                            f"(largest hole: {time_jumps.max()}, "
                            f"total: {time_jumps.sum()} = {100 * time_jumps.sum() / index_time_deltas.sum():.0f}%)")
        # Ensure we have sufficient data in general
        # At least 10 minutes -> At least 600 samples
        if len(series) < 600:
            logging.warning(f"Timeseries contains too few data points: {len(series)}")


    @staticmethod
    def groupby_individual_timeseries(data_frame):
        # Only timestamps
        if data_frame.index.nlevels == 1:
            return [(None, data_frame)]
        # MultiIndex
        return data_frame.groupby(level=non_timestamp_index(data_frame))

    def summarize(self) -> SummaryStatistics:

        clock_diff = self.get_clock_diff(abs=True)
        path_delay = self.path_delay

        data_hash = hashlib.md5(self.data.encode()).hexdigest()
        cache = SummaryStatisticCache.resolve()

        try:
            return cache.get(data_hash)
        except KeyError:
            with TimerUtil("recalculating bootstrap metrics"):
                statistics = SummaryStatistics(
                    clock_diff_median=BootstrapMetric.create(clock_diff, 0.5),
                    clock_diff_p99=BootstrapMetric.create(clock_diff, 0.99),
                    path_delay_median=BootstrapMetric.create(path_delay, 0.5),
                )

            cache.update(data_hash, statistics)
            return statistics

    def segment(self, align: pd.Series):
        """Split the series by cutting it at the midway points between the alignment points and then time shifting the series to align."""
        assert isinstance(align, pd.Series)
        assert is_timedelta64_ns_dtype(align)

        cuts = (align + align.shift(1)) / 2
        cuts.dropna(inplace=True)

        new_data = self.data_frame.copy()

        # Ensure all the aligns are inside the data
        # assert align.min() >= new_data.index.min(), f"Alignment value {align.min()} outside data frame minimum {new_data.min()}"
        # assert align.max() <= new_data.index.max(), f"Alignment value {align.max()} outside data frame maximum {new_data.max()}"

        # Divide the frame into segments.
        new_data["segment"] = np.searchsorted(cuts, new_data.index)
        # This calculates the time shifts
        new_data["alignment"] = align.loc[new_data["segment"]].values
        # new_data["cut_lower"] = cuts.loc[new_data["segment"]].values
        # new_data["cut_upper"] = cuts.loc[new_data["segment"] + 1].values

        # Align the timestamps of the frame segment by segment
        for label, group in new_data.groupby("segment"):
            assert is_number(label)
            # alignment_value = unpack_one_value(group["alignment"].unique())
            # cut_lower = unpack_one_value(group["cut_lower"].unique())
            # cut_upper = unpack_one_value(group["cut_upper"].unique())
            # assert group.index.min() <= alignment_value <= group.index.max()
            # assert cut_lower <= group.index.min() and group.index.max() <= cut_upper
            # assert cut_lower <= alignment_value <= cut_upper

        # Sort values
        new_data["timestamp"] = new_data.index - new_data["alignment"]
        new_data.set_index([COLUMN_TIMESTAMP_INDEX], inplace=True)
        # new_data.set_index(["segment", COLUMN_TIMESTAMP_INDEX], inplace=True)
        new_data.drop(columns=[
            "alignment",
            # "cut_lower", "cut_upper"
            "segment",
        ], inplace=True)
        new_data.sort_index(inplace=True)

        return Timeseries.from_series(new_data)


    @property
    def empty(self):
        return self.data_frame.empty

    def __str__(self):
        return f"Timeseries:\n{self.data_frame}"

    def memory_usage(self):
        return len(self.data) + (self._data_frame.memory_usage(deep=True).sum() if self.data_frame is not None else 0)

class MergedTimeSeries(Timeseries):

    @staticmethod
    def merge_series(original_series: Iterable[Timeseries], labels: Iterable[Any],
                     timestamp_align: bool = False) -> "MergedTimeSeries":
        """Timestamp align: We modify all timestamps so that profiles are immediately adjacent to each other (stitched)."""
        frames = []

        start_timestamp = timedelta(seconds=0)

        for series, label in zip(original_series, labels):
            frame: pd.DataFrame = series.data_frame.copy()
            frame[COLUMN_SOURCE] = label

            if timestamp_align:
                minimum_timestamp = frame.index.min()
                frame.index += start_timestamp - minimum_timestamp

                start_timestamp = frame.index.max() + timedelta(seconds=1)

            frames.append(frame)

        merged_frame = pd.concat(frames)
        assert merged_frame.index.is_unique
        return MergedTimeSeries.from_series(merged_frame)
