from dataclasses import dataclass
from typing import List, Callable, Optional, Any, Union

import pandas as pd
import seaborn
from matplotlib import pyplot as plt
from pandas.core.dtypes.common import is_numeric_dtype

from ptp_perf.charts.chart_container import ChartContainer, YAxisLabelType
from ptp_perf.models import PTPProfile
from ptp_perf.profiles.data_container import BootstrapMetric
from ptp_perf.util import unpack_one_value
from ptp_perf.utilities import units
from ptp_perf.utilities.colors import adjust_lightness
from ptp_perf.vendor.ptpd import PTPDVendor


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

@dataclass
class ComparisonChart(ChartContainer):
    title: str
    profiles: List[PTPProfile]
    x_axis_label: str
    use_bar: bool = False
    include_p99: bool = True
    include_p99_separate_axis: bool = True
    include_profile_confidence_intervals: bool = False
    include_annotate_range: bool = False
    """Whether to import the confidence intervals from each profile that is plotted."""
    include_additional_quantile_confidence_intervals: bool = False
    """Whether to compute additional aggregate quantile confidence intervals for the confidence intervals provided by seaborn."""
    hue_name: str = "Vendor"

    axes: List[List[plt.Axes]] = None
    current_axes: plt.Axes = None

    def __post_init__(self):
        self.figure, self.axes = plt.subplots(
            nrows=self.num_axis_rows, ncols=1, figsize=(10, 7),
            squeeze=False,
            # sharex="col", sharey="row",
        )

        self.plot_decorate_title(self.axes[0][0], self.title)

    def plot_statistic(self, axis: plt.Axes, profile_callback: Callable[[PTPProfile], ComparisonDataPoint],
                       linestyle=None, y_axis_label_type=YAxisLabelType.OFFSET_GENERIC):
        data_points = [profile_callback(profile).__dict__ for profile in self.profiles]
        data = pd.DataFrame(data_points)

        if data.empty:
            raise RuntimeError("No data provided to plot script.")

        indexes, values = data['hue'].factorize()
        data['dodge_x'] = indexes
        if is_numeric_dtype(data['x']):
            data['x'] += data['dodge_x']

        # Draw error bars under the actual plot
        if self.include_additional_quantile_confidence_intervals:
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
                    axis.vlines(
                        x=unpack_one_value(group["x"].unique()) + (0 if quantile == 0.5 else 0.25),
                          # + Random().randint(-2, 2),
                        ymin=bootstrap_metric.confidence_interval_lower,
                        ymax=bootstrap_metric.confidence_interval_upper,
                        color=color,
                    )

        if self.use_bar:
            # assert linestyle is None
            seaborn.barplot(
                ax=axis,
                x=data['x'],
                y=data['y'],
                hue=data['hue'].rename(self.hue_name),
                errorbar=("pi", 95),
                native_scale=True,
                linestyle=linestyle,
            )

        else:
            seaborn.lineplot(
                ax=axis,
                x=data['x'],
                y=data['y'],
                hue=data['hue'].rename(self.hue_name),
                marker='o',
                linestyle=linestyle,
                errorbar=("pi", 95),
            )

        if self.include_profile_confidence_intervals:
            axis.vlines(
                x=data['x'],
                ymin=data['y_lower_bound'],
                ymax=data['y_upper_bound'],
                color="#444444",
            )

        if self.include_annotate_range:
            axis.get_legend().set_loc("upper left")

            range = data['y'].max() - data['y'].min()
            relative_range = 100 * (range / abs(data['y'].median()))
            self.annotate(
                axis,
                f"Range: {units.format_time_offset(range)} = {relative_range:.0f}%"
            )

        self.plot_decorate_yaxis(axis, ylabel=y_axis_label_type)

        axis.set_xlabel(self.x_axis_label)


    def plot_median_clock_diff_and_path_delay(self, x_axis_values: Callable[[PTPProfile], Union[float, str]]):
        row = 0

        self.plot_statistic(
            axis=self.axes[row][0],
            profile_callback=lambda profile: ComparisonDataPoint.from_bootstrap_metric(
                x=x_axis_values(profile), y=profile.summary_statistics.clock_diff_median, hue=profile.vendor.name,
            ),
            y_axis_label_type=YAxisLabelType.CLOCK_DIFF_ABS)

        if self.include_p99:
            if self.include_p99_separate_axis:
                row += 1

            self.plot_statistic(
                axis=self.axes[row][0],
                profile_callback=lambda profile: ComparisonDataPoint.from_bootstrap_metric(
                    x=x_axis_values(profile),  # GBit/s to %
                    y=profile.summary_statistics.clock_diff_p95,
                    hue=f"{profile.vendor.name} $P_{{99}}$",
                ),
                y_axis_label_type=YAxisLabelType.CLOCK_DIFF_ABS_P99,
                linestyle='dotted',
            )

        row += 1
        self.plot_statistic(
            axis=self.axes[row][0],
            profile_callback=lambda profile: ComparisonDataPoint.from_bootstrap_metric(
                x=x_axis_values(profile),
                y=profile.summary_statistics.path_delay_median,
                hue=profile.vendor.name,
            ),
            y_axis_label_type=YAxisLabelType.PATH_DELAY)


    def set_xaxis_formatter(self, formatter):
        for row in self.axes:
            for axis in row:
                axis.xaxis.set_major_formatter(formatter)

    def plot_logx(self, base: int = 10):
        for row in self.axes:
            for axis in row:
                axis.set_xscale('log', base=base)


    @property
    def num_axis_rows(self):
        return 3 if self.include_p99 and self.include_p99_separate_axis else 2
