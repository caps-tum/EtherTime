from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, List, Any

import pandas as pd
import seaborn
from matplotlib import patheffects, pyplot as plt
from matplotlib.ticker import EngFormatter

from ptp_perf.charts.figure_container import DataElement, AxisContainer
from ptp_perf.utilities import units


@dataclass
class TimeseriesElement(DataElement):
    points: bool = True
    moving_average: bool = True
    abs: bool = True

    color: Optional[str] = None
    annotate_out_of_bounds: bool = True

    def plot(self, axis_container: AxisContainer):
        import seaborn

        data = self.get_data_as_timeseries()

        data_max = data.max()
        data_max_timestamp = data.index[data.argmax()]
        assert isinstance(data_max_timestamp, timedelta)

        if axis_container.ylimit_top:
            if not self.abs:
                raise ValueError("Unsupported combination of ylimit_top with abs=False")
            scatter_data = data[data <= axis_container.ylimit_top]
            out_of_bounds_data = data[data > axis_container.ylimit_top]
        else:
            scatter_data = data
            out_of_bounds_data = None

        # 2/3 transparent and 1/3 transparent
        color_base = self.color
        color_transparent = self.color + "55"
        color_opaque = self.color + "AA"

        if self.points:
            seaborn.scatterplot(
                ax=axis_container.axis,
                data=scatter_data,
                color=color_transparent,
                edgecolors=color_opaque,
            )

            if out_of_bounds_data is not None:
                seaborn.scatterplot(
                    ax=axis_container.axis,
                    data=out_of_bounds_data.clip(upper=axis_container.ylimit_top),
                    color=color_opaque,
                    marker='x',
                    label='_nolegend_',
                )

        if self.moving_average:
            averages = data.rolling(
                window=timedelta(seconds=30),
                center=True,
                # win_type='triang',
            ).mean()
            seaborn.lineplot(
                ax=axis_container.axis,
                data=averages,
                path_effects=[patheffects.Stroke(linewidth=2.5, foreground='black'), patheffects.Normal()],
                color=color_base,
                label='_nolegend_',
            )

        if axis_container.ylimit_top:
            if self.annotate_out_of_bounds and data_max > axis_container.ylimit_top:
                axis_container.axis.annotate(
                    f"Max: {EngFormatter(unit='s', places=0).format_data(data_max)}",
                    # xy=(data_max_timestamp.total_seconds() * units.NANOSECONDS_IN_SECOND, data_max),
                    xy=(data_max_timestamp.total_seconds() * units.NANOSECONDS_IN_SECOND, axis_container.ylimit_top),
                    xytext=(0, 2), textcoords='offset fontsize',
                    horizontalalignment='center',
                    arrowprops=dict(arrowstyle='->'),
                )


@dataclass
class ScatterElement(DataElement):
    column_style: str = None
    style_order: List[Any] = None
    color_map_as_palette: bool = False
    """By default, we use discrete colours and make the edges darkers. Use this to set the colormap directly as a palette e.g. for continuous hues."""

    def plot(self, axis_container: "AxisContainer"):
        extra_args = {
            'palette': self.color_map
        }
        if self.color_map_as_palette:
            extra_args['palette'] = {key: value + '55' for key, value in self.color_map.items() if self.color_map is not None}
            extra_args['edge_colors'] = self.data[self.column_hue].map({key: value + 'AA' for key, value in self.color_map.items()})

        scatter = seaborn.scatterplot(
            ax=axis_container.axis,
            data=self.data,
            x=self.column_x,
            y=self.column_y,
            hue=self.column_hue,
            hue_norm=self.hue_norm,
            style=self.column_style,
            style_order=self.style_order,
            **extra_args,
            # legend="auto" if axis_container.legend else False,
        )

        # cbar = plt.colorbar(
        #     scatter.collections[0],
        # )
        # cbar.set_ticks([1e-9, 1e-6, 1e-3])
        # cbar.set_ticklabels(['1ns', '1us', '1ms'])
