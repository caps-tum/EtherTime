from dataclasses import dataclass
from random import random, Random
from typing import List, Callable, Optional, Any

import pandas as pd
import seaborn
from matplotlib import pyplot as plt

from charts.chart_container import ChartContainer, YAxisLabelType
from profiles.base_profile import BaseProfile
from profiles.data_container import MergedTimeSeries, BootstrapMetric
from util import unpack_one_value
from utilities.colors import adjust_lightness
from vendor.ptpd import PTPDVendor


@dataclass
class ComparisonDataPoint:
    x: float
    y: float
    y_lower_bound: Optional[float] = None
    y_upper_bound: Optional[float] = None
    hue: Optional[Any] = None

    @staticmethod
    def from_bootstrap_metric(x: float, y: BootstrapMetric, hue: Optional[Any] = None) -> "ComparisonDataPoint":
        return ComparisonDataPoint(
            x=x,
            y=y.value,
            y_lower_bound=y.confidence_interval_lower,
            y_upper_bound=y.confidence_interval_upper,
            hue=hue,
        )

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
                       hue_name: str = None, linestyle=None, include_confidence_intervals: bool = False, use_bar: bool = False,
                       y_axis_label_type=YAxisLabelType.OFFSET_GENERIC):
        data_points = [profile_callback(profile).__dict__ for profile in self.profiles]
        data = pd.DataFrame(data_points)

        if data.empty:
            raise RuntimeError("No data provided to plot script.")

        indexes, values = data['hue'].factorize()
        data['dodge_x'] = indexes
        data['x'] += data['dodge_x']

        # Draw error bars under the actual plot
        if include_confidence_intervals:
            # Draw median = most important, last, for all vendors
            for quantile in [0.05, 0.95, 0.5]:
                for name, group in data.groupby(by=["hue", "x"]):
                    if len(group) <= 1:
                        continue

                    bootstrap_metric = BootstrapMetric.create(group["y"], quantile=quantile)
                    # if bootstrap_metric.relative_magnitude >= 0.1:
                    base_color = seaborn.color_palette()[1] if unpack_one_value(group["hue"].unique()) == PTPDVendor.name else seaborn.color_palette()[0]
                    if quantile == 0.5:
                        color = adjust_lightness(base_color, 1.4)
                    else:
                        color = adjust_lightness(base_color, 0.6)
                    self.current_axes.vlines(
                        x=unpack_one_value(group["x"].unique()) + (0 if quantile == 0.5 else 0.25),
                          # + Random().randint(-2, 2),
                        ymin=bootstrap_metric.confidence_interval_lower,
                        ymax=bootstrap_metric.confidence_interval_upper,
                        color=color,
                    )

        if use_bar:
            # assert linestyle is None
            seaborn.barplot(
                ax=self.current_axes,
                x=data['x'],
                y=data['y'],
                hue=data['hue'].rename(hue_name),
                errorbar=("pi", 95),
                native_scale=True,
                linestyle=linestyle,
            )

            self.current_axes.vlines(
                x=data['x'],
                ymin=data['y_lower_bound'],
                ymax=data['y_upper_bound'],
                color="#444444",
            )

        else:
            seaborn.lineplot(
                ax=self.current_axes,
                x=data['x'],
                y=data['y'],
                hue=data['hue'].rename(hue_name),
                marker='o',
                linestyle=linestyle,
                errorbar=("pi", 95),
            )

        self.plot_decorate_yaxis(self.current_axes, ylabel=y_axis_label_type)

        self.current_axes.set_xlabel(x_axis_label)

    def plot_statistic_timeseries_bootstrap(self, profile_get_discriminator: Callable[[BaseProfile], Any], x_axis_label: str,
                       hue_name: str = None, linestyle=None):
        merged = MergedTimeSeries.merge_series(
            [profile.time_series for profile in self.profiles],
            [profile_get_discriminator(profile) for profile in self.profiles],
            timestamp_align=True,
        )

        if merged.empty:
            raise RuntimeError("No data provided to plot script.")

        seaborn.lineplot(
            ax=self.current_axes,
            x=merged.get_discriminator(),
            y=merged.get_clock_diff(abs=True),
            # hue=data['hue'].rename(hue_name),
            marker='o',
            linestyle=linestyle,
        )
        self.plot_decorate_yaxis(self.current_axes, ylabel=YAxisLabelType.OFFSET_GENERIC)
        self.current_axes.set_xlabel(x_axis_label)


    def set_current_axes(self, row: int, col: int):
        self.current_axes = self.axes[row][col]


    def plot_median_clock_diff_and_path_delay(self, x_axis_values: Callable[[BaseProfile], float],
                                              x_axis_label="Network Utilization", include_p99: bool = False, p99_separate_axis: bool = False, use_bar: bool = False):
        row = 0
        self.set_current_axes(row, 0)

        self.plot_statistic(
            lambda profile: ComparisonDataPoint.from_bootstrap_metric(
                x=x_axis_values(profile), y=profile.summary_statistics.clock_diff_median, hue=profile.vendor.name,
            ),
            x_axis_label=x_axis_label, y_axis_label_type=YAxisLabelType.CLOCK_DIFF_ABS, hue_name="Vendor",
            include_confidence_intervals=True, use_bar=use_bar)
        # self.plot_statistic_timeseries_bootstrap(lambda profile: x_axis_values(profile),
        #                                          x_axis_label=x_axis_label, hue_name="Vendor")
        # chart.current_axes.set_yscale('log')

        if include_p99:
            if p99_separate_axis:
                row += 1
            self.set_current_axes(row, 0)

            self.plot_statistic(
                lambda profile: ComparisonDataPoint.from_bootstrap_metric(
                    x=x_axis_values(profile),  # GBit/s to %
                    y=profile.summary_statistics.clock_diff_p99,
                    hue=f"{profile.vendor.name} $P_{{99}}$",
                ),
                x_axis_label=x_axis_label, y_axis_label_type=YAxisLabelType.CLOCK_DIFF_ABS_P99, hue_name="Vendor",
                linestyle='dotted',
                include_confidence_intervals = True, use_bar = use_bar
            )

        row += 1
        self.set_current_axes(row, 0)
        self.plot_statistic(
            lambda profile: ComparisonDataPoint.from_bootstrap_metric(
                x=x_axis_values(profile),
                y=profile.summary_statistics.path_delay_median,
                hue=profile.vendor.name,
            ),
            x_axis_label=x_axis_label, y_axis_label_type=YAxisLabelType.PATH_DELAY, hue_name="Vendor",
            include_confidence_intervals=True, use_bar=use_bar)
        self.current_axes.set_ylabel('Path Delay')


    def set_xaxis_formatter(self, formatter):
        for row in self.axes:
            for axis in row:
                axis.xaxis.set_major_formatter(formatter)

    def plot_logx(self, base: int = 10):
        for row in self.axes:
            for axis in row:
                axis.set_xscale('log', base=base)

