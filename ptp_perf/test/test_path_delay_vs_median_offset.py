import unittest

import matplotlib.pyplot as plt
import seaborn

from ptp_perf.charts.chart_container import ChartContainer
from ptp_perf.constants import CHARTS_DIR, DATA_DIR, MEASUREMENTS_DIR
from ptp_perf.models.profile_query import ProfileQuery
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.vendor.registry import VendorDB


class PathDelayChartTest(unittest.TestCase):

    def test_path_delay_vs_median_offset(self):

        profiles = ProfileQuery(
            benchmark=BenchmarkDB.BASE,
        ).run()
        endpoints = [profile.endpoint_primary_slave for profile in profiles]

        fig, ax = plt.subplots(ncols=2, sharey=True)
        chart = ChartContainer(figure=fig)
        seaborn.scatterplot(
            ax=ax[0],
            x=[endpoint.path_delay_median for endpoint in endpoints],
            y=[endpoint.clock_diff_median for endpoint in endpoints],
            hue=[endpoint.profile.vendor_id for endpoint in endpoints]
        )
        chart.plot_decorate_axis(ax[0].xaxis, "Median Path Delay")
        chart.plot_decorate_axis(ax[0].yaxis, "Median Clock Offset")
        chart.plot_decorate_title(ax[0], "Path Delay Magnitude")

        seaborn.scatterplot(
            ax=ax[1],
            x=[endpoint.path_delay_std for endpoint in endpoints],
            y=[endpoint.clock_diff_median for endpoint in endpoints],
            hue=[endpoint.profile.vendor_id for endpoint in endpoints]
        )
        chart.plot_decorate_axis(ax[1].xaxis, "Path Delay Std. Dev.")
        chart.plot_decorate_axis(ax[1].yaxis, "Median Clock Offset")
        chart.plot_decorate_title(ax[1], "Path Delay Variation")


        chart.save(MEASUREMENTS_DIR.joinpath("base").joinpath("path_delay_vs_offset.png"))
