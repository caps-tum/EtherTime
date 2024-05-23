import math
import dataclasses
from dataclasses import dataclass, field
from datetime import timedelta
from io import StringIO
from pathlib import Path
from typing import Optional, List, Union, Dict, Tuple, Iterable, Self, Callable

import matplotlib
import matplotlib.ticker
import matplotlib.pyplot as plt
import pandas as pd
import seaborn
from matplotlib.ticker import MultipleLocator, PercentFormatter, LogLocator

from ptp_perf.charts.chart_container import ChartContainer
from ptp_perf.constants import PTPPERF_REPOSITORY_ROOT, PAPER_GENERATED_RESOURCES_DIR, MEASUREMENTS_DIR
from ptp_perf.profiles.benchmark import Benchmark
from ptp_perf.utilities import units

@dataclass(kw_only=True)
class DataElement:
    data: pd.DataFrame
    column_x: str = None
    column_y: str = None
    column_hue: str = None

    color_map: Optional[Dict] = field(default_factory=lambda: ChartContainer.VENDOR_COLORS)
    hue_norm: Optional[Union[tuple, matplotlib.colors.Normalize]] = None

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

    def split_data(self, x_value: Union[float, timedelta]) -> Tuple["Self", "Self"]:
        """Split the data along the x-value, returning two data elements that only differ in the data."""
        data_1 = self.data[self.data[self.column_x] < x_value]
        data_2 = self.data[self.data[self.column_x] >= x_value]
        return dataclasses.replace(self, data=data_1), dataclasses.replace(self, data=data_2)

@dataclass
class AxisContainer:
    data_elements: List[DataElement] = field(default_factory=list)

    axis: plt.Axes = None

    title: str = None
    title_kwargs: Dict = field(default_factory=dict)

    xlabel: str = None
    xlabel_options: Dict = field(default_factory=dict)
    xlog: bool = False
    xticks: Optional[Iterable] = None
    xticklabels: Optional[Iterable] = None
    xticklabels_format_time: bool = False
    xticklabels_format_time_display_offset: timedelta = timedelta(seconds=0)
    xticklabels_format_time_units_premultiplied: bool = True
    xticklabels_format_percent: bool = False
    xaxis_invert: bool = False

    ylabel: Optional[str] = None
    ylog: bool = False
    ylimit_top: Optional[float] = None
    ylimit_bottom: Optional[float] = None
    yticks: Optional[Iterable] = None
    yticklabels: Optional[Iterable] = None
    yticklabels_format_time: bool = False
    yticklabels_format_time_units_premultiplied: bool = True
    yticklabels_format_engineering: bool = False
    yticklabels_format_engineering_unit: str = ''
    yticklabels_format_percent: bool = False
    yticks_interval: Optional[float] = None

    yminorticks: bool = False
    yminorticks_fixed: Optional[List[float]] = None
    yminorticks_interval: Optional[float] = 1 * units.us
    yminorticklabels: bool = False

    legend: bool = False
    legend_pos: Optional[str] = None
    legend_kwargs: Optional[dict] = None

    grid: bool = True

    on_decorate_callbacks: List[Callable] = field(default_factory=list)

    def plot(self):
        for data_element in self.data_elements:
            data_element.plot(self)

    def decorate(self):
        self.decorate_axes()

    def decorate_axes(self):
        if self.title:
            self.axis.set_title(self.title, **self.title_kwargs)

        # X-axis
        if self.xlog:
            self.axis.set_xscale('log')
        self.axis.set_xlabel(self.xlabel, **self.xlabel_options)
        if self.xticks is not None:
            self.axis.set_xticks(self.xticks)
        if self.xticklabels_format_time:
            self.decorate_axis_time_formatter(self.axis.xaxis, offset=self.xticklabels_format_time_display_offset,
                                              units_premultiplied=self.xticklabels_format_time_units_premultiplied)
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
        if self.yticks is not None:
            self.axis.set_yticks(self.yticks)
        if self.yticklabels is not None:
            self.axis.set_yticklabels(self.yticklabels)
        if self.yticks_interval:
            self.axis.yaxis.set_major_locator(MultipleLocator(self.yticks_interval))
        if self.yticklabels_format_time:
            self.decorate_axis_time_formatter(self.axis.yaxis,
                                              units_premultiplied=self.yticklabels_format_time_units_premultiplied)
        if self.yticklabels_format_percent:
            self.axis.set_ylim(0 if self.ylimit_bottom is None else self.ylimit_bottom, 1 if self.ylimit_top is None else self.ylimit_top)
            self.axis.yaxis.set_major_formatter(PercentFormatter(xmax=1))
        if self.yticklabels_format_engineering:
            self.decorate_axis_engineering_formatter(self.axis.yaxis, self.yticklabels_format_engineering_unit)

        if self.yminorticks:
            if self.yminorticks_fixed:
                self.axis.set_yticks(self.yminorticks_fixed, minor=True)
            elif self.yminorticks_interval is not None:
                self.axis.yaxis.set_minor_locator(MultipleLocator(self.yminorticks_interval))
            else:
                if self.ylog:
                    self.axis.yaxis.set_tick_params(which="both", bottom=True)
                    # self.axis.yaxis.set_minor_locator(
                    #     matplotlib.ticker.LogLocator(base=10.0, subs=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], numticks=10)
                    # )
                    # self.axis.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())

            if self.yminorticklabels:
                self.decorate_axis_time_formatter(self.axis.yaxis, major=False,
                                                  units_premultiplied=self.yticklabels_format_time_units_premultiplied)
            else:
                self.axis.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())

        if self.grid:
            self.axis.grid(axis='y')
            self.axis.grid(axis='y', which='minor', linestyle='dotted')
            self.axis.set_axisbelow(True)

        if not self.legend:
            self.axis.legend().remove()
        else:
            if self.legend_pos or self.legend_kwargs:
                seaborn.move_legend(self.axis, self.legend_pos, **self.legend_kwargs)

        for callback in self.on_decorate_callbacks:
            callback()

    @staticmethod
    def decorate_axis_time_formatter(axis, major: bool = True, offset: timedelta = timedelta(seconds=0),
                                     units_premultiplied: bool = True):
        formatter = AxisContainer.get_time_formatter(offset, units_premultiplied)
        if major:
            axis.set_major_formatter(formatter)
        else:
            axis.set_minor_formatter(formatter)

    @staticmethod
    def get_time_formatter(offset: timedelta = timedelta(seconds=0), units_premultiplied: bool = True):
        return matplotlib.ticker.FuncFormatter(
            lambda value, _: units.format_time_offset(
                value - offset.total_seconds()
                if units_premultiplied else
                (value * units.NANOSECONDS_TO_SECONDS) - offset.total_seconds()
            )
        )

    @staticmethod
    def decorate_axis_engineering_formatter(axis, unit: str = '', major: bool = True):
        formatter = matplotlib.ticker.FuncFormatter(lambda value, _: units.format_engineering(value, unit))
        if major:
            axis.set_major_formatter(formatter)
        else:
            axis.set_minor_formatter(formatter)

    def on_decorate(self, function: Callable):
        self.on_decorate_callbacks.append(function)

    def add_boundary(self, timestamp: timedelta, linestyle='--', color='tab:red') -> "Self":
        self.on_decorate(
            lambda: self.axis.axvline(
                timestamp.total_seconds() * units.NANOSECONDS_IN_SECOND,
                linestyle=linestyle,
                color=color,
            )
        )
        return self

    def annotate(self, text: str, position: Tuple[float, float], horizontalalignment: str, verticalalignment: str):
        self.on_decorate(
            lambda: self.axis.annotate(
                text,
                xy=position,
                horizontalalignment=horizontalalignment, verticalalignment=verticalalignment,
            )
        )

    def add_elements(self, *elements: DataElement) -> Self:
        self.data_elements += elements
        return self

@dataclass
class TimeAxisContainer(AxisContainer):
    """Axis container with sensible defaults for time values on the y axis"""
    ylabel: Optional[str] = "Clock Offset"
    yticklabels_format_time: bool = True
    yticks_interval: Optional[float] = 10 * units.us

@dataclass
class TimeLogAxisContainer(TimeAxisContainer):
    ylog: bool = True
    yticks_interval: Optional[float] = None

@dataclass
class TimeseriesAxisContainer(TimeAxisContainer):
    """Axis container with sensible defaults for time series"""
    xticklabels_format_time: bool = True
    yticklabels_format_time: bool = True

@dataclass
class DataAxisContainer(AxisContainer):
    yticklabels_format_engineering: bool = True
    yticklabels_format_engineering_unit: str = 'B'


@dataclass
class FigureContainer:
    axes_containers: List[AxisContainer]

    figure: plt.Figure = None
    size: Tuple[float, float] = (6, 4)
    title: Optional[str] = None
    title_kwargs: Optional[Dict] = field(default_factory=dict)
    columns: int = None
    weights: List[int] = None
    w_space: float = None
    share_x: bool = True
    share_y: bool = True

    tight_layout: bool = False

    def plot(self):
        grid_size = self.effective_grid_size
        self.figure, axes = plt.subplots(
            figsize=self.size,
            nrows=grid_size[0], ncols=grid_size[1],
            sharex=self.share_x,
            sharey=self.share_y,
            squeeze=False,
            width_ratios=self.weights,
        )
        if self.w_space is not None:
            plt.subplots_adjust(wspace=self.w_space)

        if self.title:
            self.figure.suptitle(self.title, **self.title_kwargs)

        axes = axes.flatten()

        if len(axes) != len(self.axes_containers):
            raise RuntimeError(f"Unexpected number of axes (axes: {len(axes)}, containers: {len(self.axes_containers)})")

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

    @property
    def effective_grid_size(self):
        columns = len(self.axes_containers)
        if self.columns is not None and self.columns < columns:
            columns = self.columns
        rows = math.ceil(len(self.axes_containers) / columns)
        return rows, columns

    def save_default_locations(self, name: str, location: Union[str, Benchmark]):
        basename = location.id if isinstance(location, Benchmark) else location
        self.save(MEASUREMENTS_DIR.joinpath(basename).joinpath(f"{name}.png"), make_parents=True)
        self.save(PAPER_GENERATED_RESOURCES_DIR.joinpath(basename).joinpath(f"{name}.pdf"), make_parents=True)
