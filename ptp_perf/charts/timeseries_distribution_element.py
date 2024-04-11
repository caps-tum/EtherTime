from dataclasses import dataclass

import seaborn
import pandas as pd
from matplotlib import pyplot as plt
import matplotlib.ticker

from ptp_perf.charts.figure_container import DataElement, AxisContainer
from ptp_perf.utilities import units


@dataclass(kw_only=True)
class TimeseriesDistributionElement(DataElement):
    split: bool = True
    palette_index: int = 0
    annotate_medians: bool = False
    include_p95: bool = True
    include_iqr: bool = False

    def plot(self, axis_container: AxisContainer):
        ax = axis_container.axis

        seaborn.violinplot(
            ax=ax,
            data=self.data,
            x=self.column_x,
            y=self.column_y,
            hue=self.column_hue,
            palette=self.color_map,
            # inner="quart",
            inner=None,
            split=self.split,
            inner_kws={'color': '0.9'},
            cut=0,
            density_norm='count',
            label='_nolegend_',
        )

        data_series = self.get_data_as_timeseries()
        median = data_series.quantile(0.5)
        line = ax.axhline(median, xmax=1.05, color='black')
        line.set_clip_on(False)
        ax.annotate(
            xy=(1.07, median),
            xycoords=('axes fraction', 'data'),
            text=f"{units.format_time_offset(median)}" + (f"\n±{units.format_time_offset(data_series.std())}" if self.include_iqr else ""),
            horizontalalignment='left', verticalalignment='center',
        )
        if self.include_p95:
            p95 = data_series.quantile(0.95)
            line = ax.axhline(p95, xmax=1.05, color='black', linestyle='dashed')
            line.set_clip_on(False)
            ax.annotate(
                xy=(1.07, p95), xycoords=('axes fraction', 'data'),
                text=f"{units.format_time_offset(p95)}",
                horizontalalignment='left', verticalalignment='center',
            )
