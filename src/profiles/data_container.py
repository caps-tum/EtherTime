import datetime
import io
import logging
import math
import time
from dataclasses import dataclass
from datetime import timedelta
from functools import cached_property
from typing import Iterable, Any, Optional

import matplotlib.pyplot as plt
import matplotlib.ticker
import pandas as pd
import pandas.api.types
from matplotlib import patheffects

from utilities import units


@dataclass
class SummaryStatistics:
    clock_diff_median: Optional[float]
    clock_diff_p99: Optional[float]
    clock_diff_max: Optional[float]
    clock_diff_std: Optional[float]

    def plot_annotate(self, ax: plt.Axes):
        import matplotlib.ticker
        formatter = matplotlib.ticker.EngFormatter(unit="s", places=0, usetex=True)
        ax.annotate(
            f"Median: {formatter.format_data(self.clock_diff_median)}\n"
            f"$P_{{99}}$: {formatter.format_data(self.clock_diff_p99)}\n"
            f"Std: {formatter.format_data(self.clock_diff_std)}",
            xy=(0.95, 0.95), xycoords='axes fraction',
            verticalalignment='top', horizontalalignment='right',
        )


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
            f"Convergence Rate: {rate_formatter.format_data(self.convergence_rate)}\n",
            xy=(0.95, 0.95), xycoords='axes fraction',
            verticalalignment='top', horizontalalignment='right',
        )


COLUMN_CLOCK_DIFF = "clock_diff"


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

    def get_clock_diff(self, abs: bool) -> pd.Series:
        return self.clock_diff.abs() if abs else self.clock_diff

    def get_discriminator(self):
        return None

    @staticmethod
    def from_series(frame: pd.DataFrame):

        return Timeseries(
            Timeseries.serialize_frame(frame)
        )

    def create_convergence_criterium(self) -> pd.Series:
        resampled_data: pd.Series = self.get_clock_diff(abs=False).resample(timedelta(seconds=1)).mean()
        # rolling =
        window = 10
        rolling_means = resampled_data.rolling(window=window, center=True).mean()
        # rolling_std_devs = resampled_data.rolling(window=window, center=True).std()
        rolling_std_devs = resampled_data.std()

        confidence_interval_factor = 2.58 / math.sqrt(window)

        return (abs(rolling_means) - rolling_std_devs * confidence_interval_factor).rolling(window=10, center=True).sum()

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

    def plot_timeseries(self, ax: plt.Axes, abs: bool = True, points: bool = True, moving_average: bool = True, title: str = None, palette_index: int = 0):
        import seaborn

        data = self.get_clock_diff(abs)

        if points:
            seaborn.scatterplot(
                ax=ax,
                data=data,
                color="0.8",
                edgecolors="0.6",
            )

        if moving_average:
            averages = data.rolling(
                window=timedelta(seconds=30),
                center=True,
                # win_type='triang',
            ).mean()
            seaborn.lineplot(
                ax=ax,
                data=averages,
                path_effects=[patheffects.Stroke(linewidth=2.5, foreground='black'), patheffects.Normal()],
                color=seaborn.color_palette()[palette_index]
            )

        def format_time(value: float, _) -> str:
            delta = datetime.timedelta(microseconds=value * units.NANOSECONDS_TO_MICROSECOND)
            return str(delta)
            # value *= units.NANOSECONDS_TO_SECONDS
            # if value >= 3600:
            #     return str(value / 3600) + "h"
            # if value >= 60:
            #     return str(value / 60) + "m"
            # return str(value) + "s"

        locator = matplotlib.ticker.MaxNLocator(
            nbins=6,
            steps=[1, 3, 6, 10],
        )
        ax.xaxis.set_major_locator(locator)
        formatter = matplotlib.ticker.FuncFormatter(format_time)
        ax.xaxis.set_major_formatter(formatter)
        ax.xaxis.set_label_text("Timestamp")

        self.plot_decorate_yaxis(ax, abs)

        if title is not None:
            ax.set_title(title)

    @staticmethod
    def plot_decorate_yaxis(ax: plt.Axes, is_absolute_clockdiff):
        from matplotlib.ticker import EngFormatter

        time_offset_formatter = EngFormatter(unit='s')
        ax.yaxis.set_major_formatter(time_offset_formatter)
        ax.yaxis.set_label_text("Absolute Clock Offset" if is_absolute_clockdiff else "Clock Offset")

    def plot_timeseries_distribution(self, ax: plt.Axes, abs: bool = True, invert_axis: bool = True,
                                     discriminator_as_hue: bool = False, discriminator_as_x: bool = False, split=True):
        import seaborn

        data = self.get_clock_diff(abs)

        extra_args = {}
        if discriminator_as_hue:
            extra_args["hue"] = self.get_discriminator()
        if discriminator_as_x:
            extra_args["x"] = self.get_discriminator()

        seaborn.violinplot(
            y=data,
            inner="quart",
            split=split,
            inner_kws={'color': '0.9'},
            cut=0,
            ax=ax,
            **extra_args
        )

        if ax.get_legend():
            ax.get_legend().remove()

        if invert_axis:
            ax.invert_xaxis()

    def summarize(self) -> SummaryStatistics:
        data = self.get_clock_diff(abs=True)
        return SummaryStatistics(
            clock_diff_median=data.median(),
            clock_diff_p99=data.quantile(0.99),
            clock_diff_max=data.max(),
            clock_diff_std=data.std(),
        )

    @property
    def empty(self):
        return self.data_frame.empty


class MergedTimeSeries(Timeseries):

    @staticmethod
    def merge_series(original_series: Iterable[Timeseries], labels: Iterable[Any]):
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
