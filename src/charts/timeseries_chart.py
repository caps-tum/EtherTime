from typing import List, Union

from matplotlib import pyplot as plt

from charts.chart_container import ChartContainer
from profiles.data_container import Timeseries, SummaryStatistics, ConvergenceStatistics


class TimeseriesChart(ChartContainer):
    axes: List[plt.Axes]

    def __init__(self, title: str, timeseries: Timeseries, summary_statistics: Union[SummaryStatistics, ConvergenceStatistics] = None):
        self.figure, self.axes = plt.subplots(
            nrows=1, ncols=2, figsize=(10, 7),
            sharey=True,
            width_ratios=[0.8, 0.2],
        )
        plt.subplots_adjust(wspace=0.05)


        self.plot_timeseries(timeseries, self.axes[0], title=title)
        self.plot_timeseries_distribution(timeseries, self.axes[1])
        if summary_statistics is not None:
            summary_statistics.plot_annotate(self.axes[0])
        # self.axes[0].set_yscale('log')

