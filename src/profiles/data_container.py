import io
import logging
import math
import typing
from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable, Any, Optional, Dict

import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd

if typing.TYPE_CHECKING:
    from profiles.analysis import DetectedClockConvergence

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

            if self.confidence_interval_lower is None or self.confidence_interval_upper is None:
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
        )
        return BootstrapMetric(
            value=data.quantile(quantile),
            confidence_interval_lower=bootstrap_result.confidence_interval.low,
            confidence_interval_upper=bootstrap_result.confidence_interval.high
        )


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
    def from_convergence_series(detected_clock_convergence: "DetectedClockConvergence", convergence_series: pd.DataFrame) -> Optional["ConvergenceStatistics"]:
        convergence_max_offset = convergence_series[COLUMN_CLOCK_DIFF].abs().max()
        if math.isnan(convergence_max_offset):
            logging.warning("No convergence data on profile, cannot calculate convergence statistics.")
            return None

        if detected_clock_convergence.time.total_seconds() == 0:
            raise RuntimeError("Invalid detected clock convergence of 0 seconds.")

        return ConvergenceStatistics(
            convergence_time=detected_clock_convergence.time,
            convergence_max_offset=convergence_max_offset,
            convergence_rate=convergence_max_offset / detected_clock_convergence.time.total_seconds()
        )

    def export(self, unit_multiplier: int = 1) -> Dict:
        return {
            'Convergence Time': self.convergence_time.total_seconds(),
            'Convergence Max Offset': self.convergence_max_offset * unit_multiplier,
            'Convergence Rate': self.convergence_rate * unit_multiplier,
        }


COLUMN_CLOCK_DIFF = "clock_diff"
COLUMN_PATH_DELAY = "path_delay"
COLUMN_SOURCE = "source"


@dataclass
class Timeseries:
    data: str
    # This field doesn't have a type annotation so that pydantic will not pick it up.
    _data_frame = None

    @property
    def data_frame(self):
        if self._data_frame is None:
            read_frame = pd.read_json(io.StringIO(self.data), convert_dates=True, orient='table')
            read_frame.set_index(read_frame.index.astype("timedelta64[ns]"), inplace=True)
            self._data_frame = read_frame
        return self._data_frame

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
        serialization_frame = result_frame.copy()
        serialization_frame.index = serialization_frame.index.astype("int64")
        return serialization_frame.to_json(
            orient="table", date_unit='ns',
        )

    def validate(self, data_frame: pd.DataFrame = None, maximum_time_jump=timedelta(seconds=5)):
        if data_frame is None:
            data_frame = self.data_frame

        index_time_deltas = data_frame.index.diff()

        # Ensure that data is sorted chronologically.
        min_time_jump = index_time_deltas.min()
        if min_time_jump < timedelta(seconds=0):
            raise RuntimeError(f"Timeseries index is not monotonically increasing (minimum time difference is {min_time_jump}.")

        # Make sure there are no gaps in the data
        time_jumps = index_time_deltas[index_time_deltas >= maximum_time_jump]
        if not time_jumps.empty:
            logging.warning(f"Timeseries contains {len(time_jumps)} holes (largest hole: {time_jumps.max()}, total: {time_jumps.sum()})")


    def summarize(self) -> SummaryStatistics:

        clock_diff = self.get_clock_diff(abs=True)
        path_delay = self.path_delay

        return SummaryStatistics(
            clock_diff_median=BootstrapMetric.create(clock_diff, 0.5),
            clock_diff_p99=BootstrapMetric.create(clock_diff, 0.99),
            path_delay_median=BootstrapMetric.create(path_delay, 0.5),
        )

    @property
    def empty(self):
        return self.data_frame.empty


class MergedTimeSeries(Timeseries):

    @staticmethod
    def merge_series(original_series: Iterable[Timeseries], labels: Iterable[Any], timestamp_align: bool = False) -> "MergedTimeSeries":
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

        return MergedTimeSeries.from_series(pd.concat(frames))
