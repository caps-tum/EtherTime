from dataclasses import dataclass, field
from datetime import timedelta
from io import StringIO
from pathlib import Path
from typing import Optional, List, Union, Dict, Tuple, Iterable, Self

import matplotlib
import matplotlib.ticker
import matplotlib.pyplot as plt
import pandas as pd
import seaborn
from matplotlib.ticker import MultipleLocator, PercentFormatter

from ptp_perf.charts.chart_container import ChartContainer
from ptp_perf.constants import PTPPERF_REPOSITORY_ROOT
from ptp_perf.utilities import units

@dataclass(kw_only=True)
class DataElement:
    data: pd.DataFrame
    column_x: str = None
    column_y: str = None
    column_hue: str = None

    color_map: Dict = field(default_factory=lambda: ChartContainer.VENDOR_COLORS)

    def get_data_as_timeseries(self) -> pd.Series:
        """Get the y-data as a series indexed by x-data. Works only if there is no hue. """
        if self.column_hue is not None:
            raise NotImplementedError()

        return self.data[self.column_y].set_index(self.column_x)

    def plot(self, axis_container: "AxisContainer"):
        raise NotImplementedError()

    def configure_for_timeseries_input(self, by_vendor: bool = True) -> Self:
        self.column_x = 'timestamp'
        self.column_y = 'value'
        if by_vendor:
            self.column_hue = 'Vendor'
        return self

@dataclass
class AxisContainer:
    data_elements: List[DataElement] = field(default_factory=list)

    axis: plt.Axes = None

    title: str = None

    xlabel: str = None
    xticks: Optional[Iterable] = None
    xticklabels: Optional[Iterable] = None
    xticklabels_format_time: bool = False
    xticklabels_format_percent: bool = False
    xaxis_invert: bool = False

    ylabel: str = "Clock Offset"
    ylog: bool = False
    ylimit_top: Optional[float] = None
    ylimit_bottom: Optional[float] = None
    yticklabels_format_time: bool = True
    yticks_interval: Optional[float] = 10 * units.us

    yminorticks: bool = False
    yminorticks_interval: float = 1 * units.us
    yminorticklabels: bool = False

    legend: bool = False
    legend_pos: Optional[str] = None
    legend_kwargs: Optional[dict] = None

    grid: bool = True

    def plot(self):
        for data_element in self.data_elements:
            data_element.plot(self)

    def decorate(self):
        self.decorate_axes()

    def decorate_axes(self):
        if self.title:
            self.axis.set_title(self.title)

        # X-axis
        self.axis.xaxis.set_label_text(self.xlabel)
        if self.xticks is not None:
            self.axis.set_xticks(self.xticks)
        if self.xticklabels_format_time:
            self.decorate_axis_time_formatter(self.axis.xaxis)
        if self.xticklabels_format_percent:
            self.axis.set_xlim(0, 1)
            self.axis.xaxis.set_major_formatter(PercentFormatter(xmax=1))
        if self.xticklabels is not None:
            self.axis.set_xticklabels(self.xticklabels)
        if self.xaxis_invert:
            self.axis.xaxis.invert()

        # Y-axis
        if self.ylog:
            self.axis.set_yscale('log')
        self.axis.yaxis.set_label_text(self.ylabel)
        self.axis.set_ylim(self.ylimit_bottom, self.ylimit_top)
        if self.yticks_interval:
            self.axis.yaxis.set_major_locator(MultipleLocator(self.yticks_interval))
        if self.yticklabels_format_time:
            self.decorate_axis_time_formatter(self.axis.yaxis)

        if self.yminorticks:
            if self.yminorticks_interval:
                self.axis.yaxis.set_minor_locator(MultipleLocator(self.yminorticks_interval))
            if self.yminorticklabels:
                self.decorate_axis_time_formatter(self.axis.yaxis, major=False)

        if self.grid:
            self.axis.grid(axis='y')
            self.axis.grid(axis='y', which='minor', linestyle='dotted')
            self.axis.set_axisbelow(True)

        if not self.legend:
            self.axis.legend().remove()
        else:
            if self.legend_pos or self.legend_kwargs:
                seaborn.move_legend(self.axis, self.legend_pos, **self.legend_kwargs)

    @staticmethod
    def decorate_axis_time_formatter(axis, major: bool = True):
        formatter = matplotlib.ticker.FuncFormatter(lambda value, _: units.format_time_offset(value))
        if major:
            axis.set_major_formatter(formatter)
        else:
            axis.set_minor_formatter(formatter)

    @staticmethod
    def add_boundary(axes: plt.Axes, timestamp: timedelta):
        axes.axvline(
            timestamp.total_seconds() * units.NANOSECONDS_IN_SECOND,
            linestyle='--',
            color='tab:red'
        )

    def add_elements(self, *elements: DataElement) -> Self:
        self.data_elements += elements
        return self


@dataclass
class FigureContainer:
    axes_containers: List[AxisContainer]

    figure: plt.Figure = None
    size: Tuple[int, int] = (6, 4)
    weights: List[int] = None
    w_space: float = None
    share_y: bool = True

    tight_layout: bool = False

    def plot(self):
        self.figure, axes = plt.subplots(
            figsize=self.size,
            nrows=1, ncols=len(self.axes_containers),
            sharey=self.share_y,
            squeeze=False,
            width_ratios=self.weights,
        )
        if self.w_space is not None:
            plt.subplots_adjust(wspace=self.w_space)

        axes = axes.flatten()

        assert len(axes) == len(self.axes_containers)

        for axis, axis_container in zip(axes, self.axes_containers):
            axis_container.axis = axis
            axis_container.plot()

        for axis_container in self.axes_containers:
            axis_container.decorate()

    def save(self, path: Union[Path, str, StringIO], make_parents: bool = False, format: str = None):
        if self.tight_layout:
            self.figure.tight_layout()

        if make_parents:
            parent_path = Path(path).parent
            if not parent_path.exists() and PTPPERF_REPOSITORY_ROOT not in parent_path.parents:
                raise RuntimeError("Tried to make a path not inside the repository root.")
            parent_path.mkdir(parents=True, exist_ok=True)

        matplotlib.rcParams['pdf.fonttype'] = 42
        matplotlib.rcParams['ps.fonttype'] = 42

        if isinstance(path, Path):
            path = str(path)

        self.figure.savefig(path, format=format)
        plt.close(self.figure)

@dataclass
class TimeseriesAxisContainer(AxisContainer):
    """Axis container with sensible defaults for time series"""
    xticklabels_format_time: bool = True
    yticklabels_format_time: bool = True
