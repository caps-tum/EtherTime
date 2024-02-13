import datetime
import io
import logging
import math
import time
from dataclasses import dataclass
from datetime import timedelta
from functools import cached_property
from typing import Iterable, Any, Optional, Dict, Self

import matplotlib.pyplot as plt
import matplotlib.ticker
import pandas as pd
import pandas.api.types
from matplotlib import patheffects

from utilities import units

ANNOTATION_BBOX_PROPS = dict(boxstyle='round', facecolor=(1.0, 1.0, 1.0, 0.85), edgecolor=(0.6, 0.6, 0.6, 1.0))


@dataclass
class SummaryStatistics:
    clock_diff_median: Optional[float] = None
    clock_diff_p99: Optional[float] = None
    clock_diff_max: Optional[float] = None
    clock_diff_std: Optional[float] = None
    path_delay_median: Optional[float] = None
    path_delay_std: Optional[float] = None

    def plot_annotate(self, ax: plt.Axes):
        import matplotlib.ticker
        formatter = matplotlib.ticker.EngFormatter(unit="s", places=0, usetex=True)
        ax.annotate(
            f"Median: {formatter.format_data(self.clock_diff_median)} ± {formatter.format_data(self.clock_diff_std)}\n"
            f"$P_{{99}}$: {formatter.format_data(self.clock_diff_p99)}\n"
            f"Path Delay: {formatter.format_data(self.path_delay_median)} ± {formatter.format_data(self.path_delay_std)}",
            xy=(0.95, 0.95), xycoords='axes fraction',
            verticalalignment='top', horizontalalignment='right',
            bbox=ANNOTATION_BBOX_PROPS,
        )

    def export(self, unit_multiplier: int = 1) -> Dict:
        return {
            'Clock Difference (Median)': self.clock_diff_median * unit_multiplier,
            'Clock Difference (99-th Percentile)': self.clock_diff_p99 * unit_multiplier,
            'Clock Difference (Max)': self.clock_diff_max * unit_multiplier,
            'Clock Difference (Std)': self.clock_diff_std * unit_multiplier,
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


@dataclass
class Timeseries:
    data: str

    # @field_serializer('_data')
    # def serialize_data(self):
    #     return self._data.to_json(orient="records")

    # @classmethod
    # def parse_obj(cls, obj):
    #     return Timeseries(_data=pd.DataFrame(obj))

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
        data = self.get_clock_diff(abs=True)
        return SummaryStatistics(
            clock_diff_median=data.median(),
            clock_diff_p99=data.quantile(0.99),
            clock_diff_max=data.max(),
            clock_diff_std=data.std(),
            path_delay_median=self.path_delay.median(),
            path_delay_std=self.path_delay.std(),
        )

    @property
    def empty(self):
        return self.data_frame.empty


class MergedTimeSeries(Timeseries):

    @staticmethod
    def merge_series(original_series: Iterable[Timeseries], labels: Iterable[Any]) -> "MergedTimeSeries":
        frames = []
        for series, label in zip(original_series, labels):
            frame = series.data_frame.copy()
            frame["merge_source"] = label
            frames.append(frame)

        return MergedTimeSeries(
            Timeseries.serialize_frame(pd.concat(frames))
        )

    @staticmethod
    def check_monotonic_index(result_frame):
        # Do nothing here. The index will probably not be monotonically increasing.
        pass

    def get_discriminator(self):
        return self.data_frame["merge_source"]
