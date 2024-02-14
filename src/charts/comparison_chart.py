from dataclasses import dataclass
from typing import List, Callable, Optional, Any

import pandas as pd
import seaborn
from matplotlib import pyplot as plt

from charts.chart_container import ChartContainer, YAxisLabelType
from profiles.base_profile import BaseProfile


@dataclass
class ComparisonDataPoint:
    x: float
    y: float
    hue: Optional[Any]

class ComparisonChart(ChartContainer):
    axes: List[List[plt.Axes]]
    current_axes: plt.Axes
    profiles: List[BaseProfile]

    def __init__(self, title: str, profiles: List[BaseProfile], y_axis_decorate: bool = True, nrows=1, ncols=1):
        self.figure, self.axes = plt.subplots(
            nrows=nrows, ncols=ncols, figsize=(10, 7),
            squeeze=False,
            # sharex="col", sharey="row",
        )
        self.current_axes = self.axes[0][0]

        self.profiles = profiles
        self.plot_decorate_title(self.current_axes, title)

    def plot_statistic(self, profile_callback: Callable[[BaseProfile], ComparisonDataPoint], x_axis_label: str,
                       hue_name: str = None, linestyle=None):
        data_points = [profile_callback(profile).__dict__ for profile in self.profiles]
        data = pd.DataFrame(data_points)

        if data.empty:
            raise RuntimeError("No data provided to plot script.")

        seaborn.lineplot(
            ax=self.current_axes,
            x=data['x'],
            y=data['y'],
            hue=data['hue'].rename(hue_name),
            marker='o',
            linestyle=linestyle,
        )
        self.plot_decorate_yaxis(self.current_axes, ylabel=YAxisLabelType.OFFSET_GENERIC)

        self.current_axes.set_xlabel(x_axis_label)

    def set_current_axes(self, row: int, col: int):
        self.current_axes = self.axes[row][col]


    def plot_median_clock_diff_and_path_delay(self, x_axis_values: Callable[[BaseProfile], float],
                                              x_axis_label="Network Utilization", include_p99: bool = False):
        self.set_current_axes(0, 0)

        self.plot_statistic(lambda profile: ComparisonDataPoint(
            x=x_axis_values(profile),
            y=profile.summary_statistics.clock_diff_median,
            hue=profile.vendor.name,
        ), x_axis_label=x_axis_label, hue_name="Vendor")
        # chart.current_axes.set_yscale('log')

        if include_p99:
            self.plot_statistic(
                lambda profile: ComparisonDataPoint(
                    x=x_axis_values(profile),  # GBit/s to %
                    y=profile.summary_statistics.clock_diff_p99,
                    hue=f"{profile.vendor.name} P_{{99}}",
                ),
                x_axis_label=x_axis_label,
                hue_name="Vendor",
                linestyle='dotted',
            )

        self.set_current_axes(1, 0)
        self.plot_statistic(lambda profile: ComparisonDataPoint(
            x=x_axis_values(profile),
            y=profile.summary_statistics.path_delay_median,
            hue=profile.vendor.name,
        ), x_axis_label=x_axis_label, hue_name="Vendor")
        self.current_axes.set_ylabel('Path Delay')


    def set_xaxis_formatter(self, formatter):
        for row in self.axes:
            for axis in row:
                axis.xaxis.set_major_formatter(formatter)

    def plot_logx(self, base: int = 10):
        for row in self.axes:
            for axis in row:
                axis.set_xscale('log', base=base)

