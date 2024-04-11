from dataclasses import dataclass
from datetime import timedelta
from io import StringIO
from pathlib import Path
from typing import Optional, Union

import matplotlib.ticker
import pandas as pd
import seaborn
from matplotlib import pyplot as plt, patheffects
from matplotlib.ticker import EngFormatter
from pandas.core.dtypes.common import is_datetime64_dtype, is_timedelta64_dtype

from ptp_perf.constants import PTPPERF_REPOSITORY_ROOT
from ptp_perf.profiles.data_container import ANNOTATION_BBOX_PROPS
from ptp_perf.util import PathOrStr
from ptp_perf.utilities import units
from ptp_perf.vendor.registry import VendorDB


class YAxisLabelType:
    CLOCK_DIFF_ABS_P95 = "Absolute Clock Offset $P_{95}$"
    CLOCK_DIFF_ABS = "Absolute Clock Offset"
    CLOCK_DIFF = "Clock Offset"
    PATH_DELAY = "Path Delay"
    OFFSET_GENERIC = "Offset"


@dataclass(kw_only=True)
class ChartContainer:
    figure: plt.Figure = None

    xlabel: str = "Timestamp"
    xticks: Optional[pd.Series] = None
    xticklabels: Optional[pd.Series] = None

    ylabel: str = "Clock Offset"

    ylimit_top: Optional[float] = None
    ylimit_top_use_always: bool = False
    ylimit_bottom: Optional[float] = None
    ylog: bool = False

    legend: bool = True
    legend_pos: str = None
    legend_kwargs: dict = None

    tight_layout: bool = False

    def save(self, path: Union[Path, str, StringIO], make_parents: bool = False, include_yzero: bool = True, format: str = None):
        if self.ylog:
            for axis in self.figure.axes:
                axis.set_yscale('log')
                self.plot_decorate_yaxis(axis, "Log-Scale Clock Offset")

        if self.ylimit_top_use_always:
            for axis in self.figure.axes:
                axis.set_ylim(top=self.ylimit_top)

        if not self.ylog and include_yzero:
            for axis in self.figure.axes:
                # Ensure that the zero point is always in the view.
                ylim_current = axis.get_ylim()

                new_ylim = min(ylim_current[0], 0), max(ylim_current[1], 0)

                # Re-add an additional margin
                new_margin = 1.05

                # ylim[0] is always <= 0 and always ylim[1] >= 0, which means this will always increase the margins magnitude.
                new_ylim_with_margin = new_margin * new_ylim[0], new_margin * new_ylim[1]

                axis.set_ybound(new_ylim_with_margin)

        if self.ylimit_bottom is not None:
            for axis in self.figure.axes:
                axis.set_ybound((self.ylimit_bottom, None))

        if self.legend:
            if self.legend_pos:
                for axis in self.figure.axes:
                    seaborn.move_legend(axis, self.legend_pos, **self.legend_kwargs)
        else:
            # Remove legends
            for axis in self.figure.axes:
                axis.legend().remove()

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

    @staticmethod
    def plot_decorate_yaxis(ax: plt.Axes, ylabel: str):
        ChartContainer.plot_decorate_axis(ax.yaxis, ylabel)

    @staticmethod
    def plot_decorate_axis(axis, label: str):
        axis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(
                lambda value, _: units.format_time_offset(value)
            )
        )
        axis.set_label_text(label)

    @staticmethod
    def plot_decorate_xaxis_timeseries(ax: plt.Axes):

        locator = matplotlib.ticker.MaxNLocator(
            nbins=6,
            steps=[1, 3, 6, 10],
        )
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(
                lambda value, _: units.format_time_delta(value)
            )
        )
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

    def plot_timeseries(self, data: pd.Series, ax: plt.Axes, abs: bool = True, points: bool = True,
                        moving_average: bool = True, title: str = None, palette_index: int = 0,
                        annotate_out_of_bounds: bool = True):
        import seaborn

        if abs:
            data = data.abs()

        data_max = data.max()
        data_max_timestamp = data.index[data.argmax()]
        assert isinstance(data_max_timestamp, timedelta)

        if self.ylimit_top:
            if not abs:
                raise ValueError("Unsupported combination of ylimit_top with abs=False")
            scatter_data = data[data <= self.ylimit_top]
            out_of_bounds_data = data[data > self.ylimit_top]
        else:
            scatter_data = data
            out_of_bounds_data = None

        base_color = seaborn.color_palette()[palette_index]

        if points:
            seaborn.scatterplot(
                ax=ax,
                data=scatter_data,
                color=(*base_color, 0.3),
                edgecolors=(*base_color, 0.7),
            )

            if out_of_bounds_data is not None:
                seaborn.scatterplot(
                    ax=ax,
                    data=out_of_bounds_data.clip(upper=self.ylimit_top),
                    color=(*base_color, 0.7),
                    marker='x',
                    label='_nolegend_',
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
                color=base_color,
                label='_nolegend_',
            )

        self.plot_decorate_yaxis(ax=ax, ylabel=YAxisLabelType.CLOCK_DIFF_ABS if abs else YAxisLabelType.CLOCK_DIFF)
        self.plot_decorate_xaxis_timeseries(ax)
        self.plot_decorate_title(ax, title)

        if self.ylimit_top:
            if self.ylimit_top_use_always or data_max > self.ylimit_top:
                ax.set_ylim(top=self.ylimit_top)
            if annotate_out_of_bounds and data_max > self.ylimit_top:
                ax.annotate(
                    f"Max: {EngFormatter(unit='s', places=0).format_data(data_max)}",
                    # xy=(data_max_timestamp.total_seconds() * units.NANOSECONDS_IN_SECOND, data_max),
                    xy=(data_max_timestamp.total_seconds() * units.NANOSECONDS_IN_SECOND, self.ylimit_top),
                    xytext=(0, 2), textcoords='offset fontsize',
                    horizontalalignment='center',
                    arrowprops=dict(arrowstyle='->'),
                )

    def plot_timeseries_distribution(self, data: pd.Series, ax: plt.Axes, abs: bool = True, invert_axis: bool = True,
                                     hue_discriminator: pd.Series = None, x_discriminator: pd.Series = None, split=True,
                                     palette_index: int = 0,
                                     annotate_medians: bool = False,
                                     include_p95: bool = True, include_iqr: bool = False,):
        import seaborn

        if abs:
            data = data.abs()

        seaborn.violinplot(
            y=data,
            # inner="quart",
            inner=None,
            split=split,
            inner_kws={'color': '0.9'},
            cut=0,
            ax=ax,
            hue=hue_discriminator,
            x=x_discriminator,
            color=seaborn.color_palette()[palette_index] if hue_discriminator is None else None,
            density_norm='count',
            label='_nolegend_',
        )

        median = data.quantile(0.5)
        line = ax.axhline(median, xmax=1.05, color='black')
        line.set_clip_on(False)
        ax.annotate(
            xy=(1.07, median), xycoords=('axes fraction', 'data'),
            text=f"{units.format_time_offset(median)}" + (f"\n±{units.format_time_offset(data.std())}" if include_iqr else ""),
            horizontalalignment='left', verticalalignment='center',
        )
        if include_p95:
            p95 = data.quantile(0.95)
            line = ax.axhline(p95, xmax=1.05, color='black', linestyle='dashed')
            line.set_clip_on(False)
            ax.annotate(
                xy=(1.07, p95), xycoords=('axes fraction', 'data'),
                text=f"{units.format_time_offset(p95)}",
                horizontalalignment='left', verticalalignment='center',
            )

        if hue_discriminator is not None and annotate_medians:
            raise NotImplementedError("Cannot annotate medians with a hue discriminator.")

        if x_discriminator is not None:
            formatter = matplotlib.ticker.EngFormatter(unit="s", places=0, usetex=True)
            annotations = []
            for displacement, discriminator_value in enumerate(x_discriminator.unique()):
                discriminated_data = data[x_discriminator == discriminator_value]
                annotations.append(
                    ax.annotate(
                        text=f"{formatter.format_data(discriminated_data.median())} ±{formatter.format_data(discriminated_data.std())}",
                        xy=(displacement, discriminated_data.max()),
                        verticalalignment='bottom', horizontalalignment='center',
                    )
                )
                # ax.margins(y=0.2)

            # Redraw the figure to make annotations fit
            # print(f"Limits: {formatter.format_data(ax.get_ylim()[1])} Margins: {ax.margins()}")
            self.figure.draw_without_rendering()

            bboxes = []
            for index, annotation in enumerate(annotations):
                bbox = annotation.get_window_extent()
                # print(f"Annotation view {index}: {formatter.format_data(min(y for _, y in bbox.corners())), formatter.format_data(max(y for _, y in bbox.corners()))}")
                bbox_data = bbox.transformed(ax.transData.inverted())
                bboxes.append(bbox_data)
                # print(f"Annotation {index}: {formatter.format_data(min(y for _, y in bbox_data.corners())), formatter.format_data(max(y for _, y in bbox_data.corners()))}")

            for box in bboxes:
                ax.update_datalim(box.corners())
            ax.margins(0.1)
            ax.autoscale_view()
            # print(f"Limits after: {formatter.format_data(ax.get_ylim()[1])} Margins: {ax.margins()}")

        if ax.get_legend():
            ax.get_legend().remove()

        if invert_axis:
            ax.invert_xaxis()

        if abs:
            pass
            # ax.update_datalim(((0, 0),), updatex=False)

    def annotate(self, ax: plt.Axes, annotation: str, position=(0.95, 0.95), horizontalalignment: str = "right",
                 verticalalignment: str = 'top'):
        ax.annotate(
            annotation,
            xy=position, xycoords='axes fraction',
            verticalalignment=verticalalignment, horizontalalignment=horizontalalignment,
            bbox=ANNOTATION_BBOX_PROPS,
        )

    VENDOR_COLORS = {
        VendorDB.PTPD.id: '#1f77b4',
        VendorDB.PTPD.name: '#1f77b4',
        VendorDB.LINUXPTP.id: '#ff7f0e',
        VendorDB.LINUXPTP.name: '#ff7f0e',
        VendorDB.SPTP.id: '#2ca02c',
        VendorDB.SPTP.name: '#2ca02c',
        VendorDB.CHRONY.id: '#d62728',
        VendorDB.CHRONY.name: '#d62728',
    }

    @staticmethod
    def calculate_vendor_color(vendor_data: pd.Series):
        return vendor_data.apply(lambda x: ChartContainer.VENDOR_COLORS[x])
