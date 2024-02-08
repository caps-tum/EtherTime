from typing import List, Self, Any, Iterable

import seaborn
from matplotlib import pyplot as plt

from charts.chart_container import ChartContainer, YAxisLabelType
from profiles.base_profile import BaseProfile
from profiles.data_container import MergedTimeSeries


class TimeSeriesChartComparison(ChartContainer):
    axes: List[plt.Axes]

    def __init__(self, profiles: Iterable[BaseProfile], labels: Iterable[Any], x_label: str):
        self.figure, self.axes = plt.subplots(
            nrows=2, ncols=1, figsize=(14, 7),
        )

        merged_series = MergedTimeSeries.merge_series(
            original_series=[profile.time_series for profile in profiles],
            labels=labels,
        )

        self.plot_timeseries_distribution(
            merged_series.clock_diff,
            self.axes[0],
            invert_axis=False,
            split=False,
            x_discriminator=merged_series.get_discriminator()
        )
        self.plot_decorate_yaxis(
            self.axes[0], ylabel=YAxisLabelType.CLOCK_DIFF_ABS,
        )
        self.axes[1].xaxis.set_label_text(None)

        self.plot_timeseries_distribution(
            merged_series.path_delay,
            self.axes[1],
            invert_axis=False,
            split=False,
            x_discriminator=merged_series.get_discriminator(),
            palette_index=3,
        )

        self.plot_decorate_yaxis(
            self.axes[1], ylabel=YAxisLabelType.PATH_DELAY,
        )

        self.axes[1].xaxis.set_label_text(x_label)
