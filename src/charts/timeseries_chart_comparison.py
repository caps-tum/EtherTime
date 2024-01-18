from typing import List, Self, Any, Iterable

import seaborn
from matplotlib import pyplot as plt

from charts.chart_container import ChartContainer
from profiles.base_profile import BaseProfile
from profiles.data_container import MergedTimeSeries


class TimeSeriesChartComparison(ChartContainer):
    axes: plt.Axes

    def __init__(self, profiles: Iterable[BaseProfile], labels: Iterable[Any]):
        self.figure, self.axes = plt.subplots(
            nrows=1, ncols=1, figsize=(18, 7),
        )

        merged_series = MergedTimeSeries.from_series(
            original_series=[profile.time_series for profile in profiles],
            labels=labels,
        )

        merged_series.plot_timeseries_distribution(
            self.axes,
            invert_axis=False,
            split=False,
            discriminator_as_x=True
        )
        merged_series.plot_decorate_yaxis(
            self.axes, is_absolute_clockdiff=True
        )
        self.axes.xaxis.set_label_text("Profile Date")
