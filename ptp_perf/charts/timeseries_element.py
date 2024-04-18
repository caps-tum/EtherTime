from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

import pandas as pd
import seaborn
from matplotlib import patheffects
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


class ScatterElement(DataElement):

    def plot(self, axis_container: "AxisContainer"):
        seaborn.scatterplot(
            self.data,
            x=self.column_x,
            y=self.column_y,
            hue=self.column_hue,
        )
