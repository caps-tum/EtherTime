from typing import List

from matplotlib import pyplot as plt

from ptp_perf.charts.chart_container import ChartContainer
from ptp_perf.models import Sample
from ptp_perf.models.sample_query import SampleQuery
from ptp_perf.profiles.base_profile import BaseProfile
from ptp_perf.profiles.data_container import MergedTimeSeries


class TimeSeriesChartVersus(ChartContainer):
    axes: List[plt.Axes]

    def __init__(self, query1: SampleQuery, query2: SampleQuery, include_path_delay: bool = False):
        self.figure, self.axes = plt.subplots(
            nrows=1, ncols=3, figsize=(18, 7),
            sharey=True,
            width_ratios=[0.45, 0.1, 0.45],
        )
        plt.subplots_adjust(wspace=0.05)

        self.plot_timeseries(query1.run(Sample.SampleType.CLOCK_DIFF), self.axes[0])
        # profile1.summary_statistics.plot_annotate(self.axes[0])

        if include_path_delay:
            self.plot_timeseries(profile1.time_series.path_delay, self.axes[0], palette_index=3)


        self.plot_timeseries(profile2.time_series.clock_diff, self.axes[2], title=profile2.get_title(), palette_index=1)
        profile2.summary_statistics.plot_annotate(self.axes[2])

        if include_path_delay:
            self.plot_timeseries(profile2.time_series.path_delay, self.axes[2], palette_index=3)
        self.axes[2].set_ylabel(None)

        merge_series = MergedTimeSeries.merge_series(
            [profile1.time_series, profile2.time_series],
            labels=[0, 1],
            timestamp_align=True,
        )
        self.plot_timeseries_distribution(
            merge_series.clock_diff,
            self.axes[1],
            invert_axis=False,
            hue_discriminator=merge_series.get_discriminator(),
        )

    def set_titles(self, title1: str, title2: str):
        self.axes[0].set_title(title1)
        self.axes[2].set_title(title2)
        return self
