from typing import List, Any, Iterable

from matplotlib import pyplot as plt

from ptp_perf.charts.chart_container import ChartContainer, YAxisLabelType
from ptp_perf.models import Sample
from ptp_perf.models.sample_query import SampleQuery
from ptp_perf.profiles.data_container import MergedTimeSeries


class DistributionComparisonChart(ChartContainer):
    axes: List[plt.Axes]

    def __init__(self, queries: Iterable[SampleQuery], labels: Iterable[Any], x_label: str):
        self.figure, self.axes = plt.subplots(
            nrows=2, ncols=1, figsize=(14, 7),
        )

        merged_series = MergedTimeSeries.merge_series(
            original_series=[query.run(Sample.SampleType.CLOCK_DIFF) for query in queries],
            labels=labels,
            timestamp_align=True,
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
