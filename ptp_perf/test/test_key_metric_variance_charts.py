from unittest import TestCase

import matplotlib

from ptp_perf.charts.comparison_chart import ComparisonChart
from ptp_perf.models.profile_query import ProfileQuery
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.util import str_join
from ptp_perf.vendor.registry import VendorDB


class KeyMetricVarianceCharts(TestCase):

    def test_chart(self):
        # matplotlib.rcParams['text.usetex'] = True
        # import matplotlib.font_manager
        # fpaths = matplotlib.font_manager.findSystemFonts()
        #
        # for i in fpaths:
        #     f = matplotlib.font_manager.get_font(i)
        #     print(f.family_name, f.fname)
        #
        # matplotlib.rcParams['font.family'] = 'cmr10'


        for benchmark in BenchmarkDB().all():
            profile_query = ProfileQuery(benchmark=benchmark)
            endpoints = [profile.endpoint_primary_slave for profile in profile_query.run()]
            if len(endpoints) == 0:
                continue

            comparison_chart = self.create_key_metric_variance_chart(endpoints)

            comparison_chart.save(benchmark.storage_base_path.joinpath(f"key_metric_variance.svg"))
            comparison_chart.save(benchmark.storage_base_path.joinpath(f"key_metric_variance.pdf"))

    @staticmethod
    def create_key_metric_variance_chart(endpoints, true=True) -> ComparisonChart:
        benchmark_names = str_join(set([endpoint.benchmark.name for endpoint in endpoints]))
        endpoints.sort(key=lambda endpoint: VendorDB.ANALYZED_VENDORS.index(endpoint.profile.vendor))
        comparison_chart = ComparisonChart(
            title=f"Reproducibility ({benchmark_names})",
            endpoints=endpoints,
            x_axis_label="Profile",
            use_bar=True,
            include_p99=False, include_p99_separate_axis=False,
            include_profile_confidence_intervals=True,
            include_annotate_range=True,
            ylimit_top=0.0001, ylimit_top_use_always=true,
        )
        comparison_chart.plot_median_clock_diff_and_path_delay(
            x_axis_values=lambda endpoint: endpoints.index(endpoint),
        )
        return comparison_chart
