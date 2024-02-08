from datetime import timedelta
from pathlib import Path

import matplotlib.ticker
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import pyplot as plt, patheffects

from profiles.data_container import Timeseries
from util import PathOrStr
from utilities import units

class YAxisLabelType:
    CLOCK_DIFF_ABS = "Absolute Clock Offset"
    CLOCK_DIFF = "Clock Offset"
    PATH_DELAY = "Path Delay"
    OFFSET_GENERIC = "Offset"


class ChartContainer:
    figure: plt.Figure


    def save(self, path: PathOrStr, make_parent: bool = False):
        if make_parent:
            Path(path).parent.mkdir(exist_ok=True)
        self.figure.savefig(str(path))
        plt.close(self.figure)


    @staticmethod
    def plot_decorate_yaxis(ax: plt.Axes, ylabel: str):
        from matplotlib.ticker import EngFormatter

        time_offset_formatter = EngFormatter(unit='s')
        ax.yaxis.set_major_formatter(time_offset_formatter)
        ax.yaxis.set_label_text(ylabel)


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

    def plot_timeseries(self, data: pd.Series, ax: plt.Axes, abs: bool = True, points: bool = True, moving_average: bool = True, title: str = None, palette_index: int = 0):
        import seaborn

        if abs:
            data = data.abs()

        self.plot_decorate_yaxis(ax=ax, ylabel=YAxisLabelType.CLOCK_DIFF_ABS if abs else YAxisLabelType.CLOCK_DIFF)
        self.plot_decorate_xaxis_timeseries(ax)
        self.plot_decorate_title(ax, title)

        base_color = seaborn.color_palette()[palette_index]

        if points:
            seaborn.scatterplot(
                ax=ax,
                data=data,
                color=(*base_color, 0.3),
                edgecolors=(*base_color, 0.7),
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
                color=base_color
            )

    def plot_timeseries_distribution(self, data: pd.Series, ax: plt.Axes, abs: bool = True, invert_axis: bool = True,
                                     hue_discriminator: pd.Series = None, x_discriminator: pd.Series = None, split=True, palette_index: int = 0):
        import seaborn

        if abs:
            data = data.abs()

        seaborn.violinplot(
            y=data,
            inner="quart",
            split=split,
            inner_kws={'color': '0.9'},
            cut=0,
            ax=ax,
            hue=hue_discriminator,
            x=x_discriminator,
            color=seaborn.color_palette()[palette_index] if hue_discriminator is None else None,
            density_norm='count',
        )

        if ax.get_legend():
            ax.get_legend().remove()

        if invert_axis:
            ax.invert_xaxis()
