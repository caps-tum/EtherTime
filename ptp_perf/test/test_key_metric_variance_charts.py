from typing import List

import pandas as pd
from django.test import TestCase

from ptp_perf import config
from ptp_perf.charts.comparison_bar_element import ComparisonBarElement
from ptp_perf.charts.comparison_chart import ComparisonChart
from ptp_perf.charts.figure_container import FigureContainer, TimeAxisContainer
from ptp_perf.constants import PAPER_GENERATED_RESOURCES_DIR
from ptp_perf.models import PTPEndpoint, PTPProfile
from ptp_perf.models.profile_query import ProfileQuery
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.util import str_join
from ptp_perf.utilities.pandas_utilities import frame_column, foreign_frame_column
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

        for benchmark in [BenchmarkDB().BASE]:
            for cluster in config.ANALYZED_CLUSTERS:
                profile_query = ProfileQuery(benchmark=benchmark, cluster=cluster)
                endpoints = [profile.endpoint_primary_slave for profile in profile_query.run()]
                if len(endpoints) == 0:
                    continue

                comparison_chart = self.create_key_metric_variance_chart(endpoints)

                comparison_chart.save(benchmark.storage_base_path.joinpath(f"key_metric_variance_{cluster.id}.svg"))
                comparison_chart.save(benchmark.storage_base_path.joinpath(f"key_metric_variance_{cluster.id}.pdf"))

            endpoints = [profile.endpoint_primary_slave for profile in ProfileQuery(benchmark=benchmark, cluster=config.CLUSTER_PI).run()]
            endpoints_pi5 = [profile.endpoint_primary_slave for profile in ProfileQuery(benchmark=benchmark, cluster=config.CLUSTER_PI5).run()]
            comparison_chart = self.create_key_metric_variance_chart(endpoints)
            comparison_chart.axes_containers += self.create_key_metric_variance_chart(endpoints_pi5).axes_containers
            comparison_chart.columns = 1
            comparison_chart.share_x = False
            comparison_chart.share_y = False
            comparison_chart.axes_containers
            comparison_chart.plot()
            comparison_chart.save(benchmark.storage_base_path.joinpath(f"key_metric_variance_compare_pi.svg"))
            comparison_chart.save(PAPER_GENERATED_RESOURCES_DIR.joinpath(f"key_metric_variance_compare_pi.pdf"))


    @staticmethod
    def create_key_metric_variance_chart(endpoints: List[PTPEndpoint],
                                         ylimit_top_use_always=True) -> FigureContainer:
        expansions = ["profile"]
        frame = pd.DataFrame(data=(
            {
                key: value
                for key, value in endpoint.__dict__.items()
                if not key.startswith("_")
            } | {
                    f"{expansion}__{key}": value
                    for expansion in expansions
                    for key, value in endpoint.__getattribute__(expansion).__dict__.items()
                    if not key.startswith("_")
            }
            for endpoint in sorted(endpoints, key=lambda endpoint: VendorDB.ANALYZED_VENDORS.index(endpoint.profile.vendor))
        ))
        melted_frame = frame.melt(
            id_vars=[
                frame_column(PTPEndpoint.profile),
                foreign_frame_column(PTPEndpoint.profile, PTPProfile.vendor_id)
            ],
            value_vars=[
                frame_column(PTPEndpoint.clock_diff_p05),
                frame_column(PTPEndpoint.clock_diff_median),
                frame_column(PTPEndpoint.clock_diff_p95),
            ]
        )
        # The "primary key" is the profile id, but it needs to be a string otherwise it will get sorted.
        melted_frame['x'] = melted_frame[
            frame_column(PTPEndpoint.profile)
        ].astype(str)

        print(melted_frame)

        chart = FigureContainer(
            axes_containers=[
                TimeAxisContainer(
                    data_elements=[
                        ComparisonBarElement(
                            data=melted_frame,
                            column_x='x',
                            column_y='value',
                            column_hue='profile__vendor_id',
                            native_scale=False,
                        )
                    ],
                    xticks=[],
                    title='Baseline Variance across Trials',
                )
            ],
        )
        chart.plot()

        return chart

    @staticmethod
    def create_key_metric_variance_chart_old(endpoints, ylimit_top_use_always=True) -> ComparisonChart:
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
            ylimit_top=0.0001, ylimit_top_use_always=ylimit_top_use_always,
        )
        comparison_chart.plot_median_clock_diff_and_path_delay(
            x_axis_values=lambda endpoint: endpoints.index(endpoint),
        )
        return comparison_chart
