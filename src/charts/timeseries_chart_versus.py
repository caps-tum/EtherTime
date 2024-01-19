from typing import List, Self

import seaborn
from matplotlib import pyplot as plt

from charts.chart_container import ChartContainer
from profiles.base_profile import BaseProfile
from profiles.data_container import MergedTimeSeries


class TimeSeriesChartVersus(ChartContainer):
    axes: List[plt.Axes]

    def __init__(self, profile1: BaseProfile, profile2: BaseProfile):
        self.figure, self.axes = plt.subplots(
            nrows=1, ncols=3, figsize=(18, 7),
            sharey=True,
            width_ratios=[0.45, 0.1, 0.45],
        )
        plt.subplots_adjust(wspace=0.05)

        profile1.time_series.plot_timeseries(self.axes[0], title=profile1.id)
        profile1.summary_statistics.plot_annotate(self.axes[0])

        profile2.time_series.plot_timeseries(self.axes[2], title=profile2.id, palette_index=1)
        profile2.summary_statistics.plot_annotate(self.axes[2])

        merge_series = MergedTimeSeries.merge_series(
            [profile1.time_series, profile2.time_series],
            labels=[0, 1]
        )
        merge_series.plot_timeseries_distribution(
            self.axes[1],
            invert_axis=False,
            discriminator_as_hue=True,
        )

    def set_titles(self, title1: str, title2: str):
        self.axes[0].set_title(title1)
        self.axes[2].set_title(title2)
        return self
