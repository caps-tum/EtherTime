from dataclasses import dataclass
from typing import List, Union

import pandas as pd
from matplotlib import pyplot as plt

from ptp_perf.charts.chart_container import ChartContainer
from ptp_perf.profiles.data_container import Timeseries, SummaryStatistics, ConvergenceStatistics


@dataclass
class TimeseriesChart(ChartContainer):
    title: str = None
    summary_statistics:  Union[SummaryStatistics, ConvergenceStatistics] = None
    axes: List[plt.Axes] = None

    def __post_init__(self):
        self.figure, self.axes = plt.subplots(
            nrows=1, ncols=2, figsize=(10, 7),
            sharey=True,
            width_ratios=[0.8, 0.2],
        )
        plt.subplots_adjust(wspace=0.05)

        self.plot_decorate_title(ax=self.axes[0], title=self.title)

        if self.summary_statistics is not None:
            self.summary_statistics.plot_annotate(self.axes[0])
        # self.axes[0].set_yscale('log')


    def add_clock_difference(self, series: pd.Series):
        self.plot_timeseries(series, self.axes[0], abs=True)
        self.plot_timeseries_distribution(series, self.axes[1])


    def add_path_delay(self, series: pd.Series):
        self.plot_timeseries(series, ax=self.axes[0], palette_index=3)
        self.plot_timeseries_distribution(series, self.axes[1], palette_index=3)
