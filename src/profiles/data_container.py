import io
from dataclasses import dataclass
from datetime import timedelta
from functools import cached_property
from typing import Iterable, Any, Optional, Dict

import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd

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

    @cached_property
    def data_frame(self):
        read_frame = pd.read_json(io.StringIO(self.data), convert_dates=True, orient='table')
        read_frame.set_index(read_frame.index.astype("timedelta64[ns]"), inplace=True)
        self.check_monotonic_index(read_frame)
        return read_frame

    @property
    def clock_diff(self) -> pd.Series:
        return self.data_frame[COLUMN_CLOCK_DIFF]

    @property
    def path_delay(self) -> pd.Series:
        return self.data_frame[COLUMN_PATH_DELAY]

    def get_clock_diff(self, abs: bool) -> pd.Series:
        return self.clock_diff.abs() if abs else self.clock_diff

    def get_discriminator(self):
        return None

    @staticmethod
    def from_series(frame: pd.DataFrame):

        return Timeseries(
            Timeseries.serialize_frame(frame)
        )

    @staticmethod
    def serialize_frame(result_frame):
        serialization_frame = result_frame.copy()
        serialization_frame.index = serialization_frame.index.astype("int64")
        return serialization_frame.to_json(
            orient="table", date_unit='ns',
        )

    @staticmethod
    def check_monotonic_index(result_frame):
        if not result_frame.index.is_monotonic_increasing:
            raise RuntimeError("Timeseries index is not monotonically increasing.")


    def summarize(self) -> SummaryStatistics:
        import scipy.stats

        clock_diff = self.get_clock_diff(abs=True)
        path_delay = self.path_delay

        # Samples must be in a sequence, this isn't clear from the documentation
        # https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html
        bootstrap_clock_diff_median = scipy.stats.bootstrap(
            (clock_diff,), np.median, random_state=0,
        )
        bootstrap_clock_diff_p99 = scipy.stats.bootstrap(
            (clock_diff,), lambda sample: np.quantile(sample, 0.99), random_state=0,
        )
        bootstrap_path_delay_median = scipy.stats.bootstrap(
            (path_delay,), np.median, random_state=0,
        )

        return SummaryStatistics(
            clock_diff_median=BootstrapMetric(clock_diff.median(), bootstrap_clock_diff_median.confidence_interval[0], bootstrap_clock_diff_median.confidence_interval[1]),
            clock_diff_p99=BootstrapMetric(clock_diff.quantile(0.99), bootstrap_clock_diff_p99.confidence_interval[0], bootstrap_clock_diff_p99.confidence_interval[1]),
            path_delay_median=BootstrapMetric(path_delay.median(), bootstrap_path_delay_median.confidence_interval[0], bootstrap_path_delay_median.confidence_interval[1]),
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

        return MergedTimeSeries(
            Timeseries.serialize_frame(pd.concat(frames))
        )

    @staticmethod
    def check_monotonic_index(result_frame):
        # Do nothing here. The index will probably not be monotonically increasing.
        pass

    def get_discriminator(self):
        return self.data_frame[COLUMN_SOURCE]
