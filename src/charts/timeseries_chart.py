from typing import List

import seaborn
from matplotlib import pyplot as plt

from charts.chart_container import ChartContainer
from profiles.base_profile import BaseProfile
from util import PathOrStr


class TimeseriesChart(ChartContainer):
    axes: List[plt.Axes]

    def __init__(self, profile: BaseProfile, include_convergence_criterium: bool = False):
        self.fig, self.axes = plt.subplots(
            nrows=1, ncols=2, figsize=(10, 7),
            sharey=True,
            width_ratios=[0.8, 0.2],
        )
        plt.subplots_adjust(wspace=0.05)

        profile.time_series.plot_timeseries(self.axes[0], title=profile.id)
        profile.time_series.plot_timeseries_distribution(self.axes[1])
        profile.summary_statistics.plot_annotate(self.axes[0])

        if include_convergence_criterium:
            secondary_axis = self.axes[0].twinx()
            seaborn.lineplot(
                data=profile.time_series.create_convergence_criterium(),
                ax=secondary_axis
            )

    def save(self, path: PathOrStr):
        plt.savefig(str(path))
