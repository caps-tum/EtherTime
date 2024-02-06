from datetime import timedelta
from pathlib import Path

import matplotlib.ticker
import matplotlib.pyplot as plt
from matplotlib import pyplot as plt, patheffects

from profiles.data_container import Timeseries
from util import PathOrStr
from utilities import units


class ChartContainer:
    figure: plt.Figure


    def save(self, path: PathOrStr, make_parent: bool = False):
        if make_parent:
            Path(path).parent.mkdir(exist_ok=True)
        self.figure.savefig(str(path))
        plt.close(self.figure)


    @staticmethod
    def plot_decorate_yaxis(ax: plt.Axes, is_absolute_clockdiff: bool):
        from matplotlib.ticker import EngFormatter

        time_offset_formatter = EngFormatter(unit='s')
        ax.yaxis.set_major_formatter(time_offset_formatter)
        ax.yaxis.set_label_text("Absolute Clock Offset" if is_absolute_clockdiff else "Clock Offset")


    @staticmethod
    def plot_decorate_xaxis_timeseries(ax: plt.Axes):

        def format_time(value: float, _) -> str:
            delta = timedelta(microseconds=value * units.NANOSECONDS_TO_MICROSECOND)
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


    @staticmethod
    def add_boundary(axes: plt.Axes, timestamp: timedelta):
        axes.axvline(
            timestamp.total_seconds() * units.NANOSECONDS_IN_SECOND,
            linestyle='--',
            color='tab:red'
        )

    @staticmethod
    def plot_decorate_title(ax, title):
        if title is not None:
            ax.set_title(title)

    def plot_timeseries(self, timeseries: Timeseries, ax: plt.Axes, abs: bool = True, points: bool = True, moving_average: bool = True, title: str = None, palette_index: int = 0):
        import seaborn

        data = timeseries.get_clock_diff(abs)

        self.plot_decorate_yaxis(ax=ax, is_absolute_clockdiff=abs)
        self.plot_decorate_xaxis_timeseries(ax)
        self.plot_decorate_title(ax, title)

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

    def plot_timeseries_distribution(self, timeseries: Timeseries, ax: plt.Axes, abs: bool = True, invert_axis: bool = True,
                                     discriminator_as_hue: bool = False, discriminator_as_x: bool = False, split=True):
        import seaborn

        data = timeseries.get_clock_diff(abs)

        extra_args = {}
        if discriminator_as_hue:
            extra_args["hue"] = timeseries.get_discriminator()
        if discriminator_as_x:
            extra_args["x"] = timeseries.get_discriminator()

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
