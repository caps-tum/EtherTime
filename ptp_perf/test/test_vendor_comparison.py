from typing import List
from unittest import TestCase

import pandas as pd
from matplotlib.patches import ConnectionPatch, ConnectionStyle

from ptp_perf import config
from ptp_perf.charts.comparison_bar_element import ComparisonBarElement, ComparisonLineElement
from ptp_perf.charts.figure_container import FigureContainer, AxisContainer
from ptp_perf.constants import MEASUREMENTS_DIR, PAPER_GENERATED_RESOURCES_DIR
from ptp_perf.models import Sample
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.models.exceptions import NoDataError
from ptp_perf.models.sample_query import SampleQuery
from ptp_perf.profiles.base_profile import ProfileTags
from ptp_perf.profiles.benchmark import Benchmark
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.utilities import units
from ptp_perf.vendor.registry import VendorDB


class VendorComparisonCharts(TestCase):

    def test_load_chart(self):
        for cluster in [config.CLUSTER_PI, config.CLUSTER_PI5]:
            benchmarks = BenchmarkDB.all_by_tags(ProfileTags.COMPONENT_NET, ProfileTags.ISOLATION_UNPRIORITIZED)
            benchmarks = [benchmark for benchmark in benchmarks if benchmark.artificial_load_network in [200, 500, 800, 1000]]
            benchmarks.append(BenchmarkDB.BASE)

            frame = self.collect_quantile_data(benchmarks, clusters=[cluster])
            frame['X'] = frame['Benchmark Id'].apply(lambda x: BenchmarkDB.get(x).artificial_load_network) / 1000
            frame.sort_values('X', inplace=True)
            print(frame)

            chart = FigureContainer(
                axes_containers=[
                    AxisContainer([
                            ComparisonLineElement(
                                data=frame,
                                column_x='X',
                                column_y='Value',
                                column_hue='Vendor',
                            )
                        ],
                        title="Unisolated Network Load",
                        xlabel='Network Load',
                        xticklabels_format_time=False,
                        xticklabels_format_percent=True,
                        ylog=True,
                        yticks_interval=None,
                    )
                ]
            )
            chart.plot()
            chart.save(MEASUREMENTS_DIR.joinpath("load").joinpath(f"unprioritized_trend_{cluster.id}.png"))

    def test_vendor_chart(self):
        benchmark = BenchmarkDB.BASE
        frame = self.collect_quantile_data([benchmark])

        frame['X'] = (len(VendorDB.ANALYZED_VENDORS) + 0.5) * frame['Cluster Index'] + frame['Vendor Index']
        frame.sort_values('X', inplace=True)
        print(frame)


        frame_rpi5 = frame[frame['Cluster'] == config.CLUSTER_PI5.name]

        chart = FigureContainer(
            size=(8, 4),
            weights=[2.5, 1],
            w_space=0,
            share_y=False,
            tight_layout=True,
            axes_containers=[
                AxisContainer(
                    [ComparisonBarElement(
                        data=frame,
                        column_x='X',
                        column_y='Value',
                        column_hue='Vendor'
                    )],
                    title="Baseline Performance by Vendor and Cluster",
                    xticks=list(frame['X']) + [1.5, 6],
                    xticklabels=list(frame['Vendor']) + ["\nRaspberry-Pi 4", "\nRaspberry-Pi 5"],
                    ylimit_top=50 * units.us,
                ),
                AxisContainer(
                    [ComparisonBarElement(
                        data=frame_rpi5,
                        column_x='X',
                        column_y='Value',
                        column_hue='Vendor'
                    )],
                    xticks=list(frame_rpi5['X']) + [6],
                    xticklabels=list(frame_rpi5['Vendor']) + ["\nRaspberry-Pi 5"],
                    ylabel='',
                    ylimit_top=5.5 * units.us,
                    yminorticks=True,
                    yminorticklabels=True,
                )
            ],
        )
        chart.plot()
        ax1 = chart.axes_containers[0].axis
        ax2 = chart.axes_containers[1].axis
        boundary = 5 * units.us
        ax1.add_artist(
            ConnectionPatch(
                (1.0, boundary / ax1.get_ylim()[1]), (0.5, 0),
                coordsA='axes fraction', coordsB='axes fraction',
                axesA=ax1, axesB=ax1,
                linestyle='dashed', color='0.7', connectionstyle=ConnectionStyle('angle', angleA=180, angleB=90, rad=0),
            )
        )
        ax2.axhline(boundary, linestyle='--', color='0.7', zorder=0.5)
        ax2.add_artist(
            ConnectionPatch(
                (1.0, boundary / ax1.get_ylim()[1]), (-0.2, boundary / ax2.get_ylim()[1]),
                coordsA='axes fraction', coordsB='axes fraction',
                axesA=ax1, axesB=ax2,
                linestyle='dashed', color='0.7', connectionstyle=ConnectionStyle('arc', angleA=0, angleB=180, armA=5, armB=5, rad=5),
            )
        )

        chart.save(MEASUREMENTS_DIR.joinpath(benchmark.id).joinpath("vendor_comparison.png"))
        chart.save(PAPER_GENERATED_RESOURCES_DIR.joinpath(benchmark.id).joinpath("vendor_comparison.pdf"))

        output = "\\ptpperfLoadKeys{\n"
        for index, row in frame.iterrows():
            output += f"    /ptpperf/{row['Benchmark Id']}/{row['Cluster Id']}/{row['Vendor Id']}/q{int(row['Quantile'] * 100)}/.initial={row['Value']},\n"
        output += "}\n"
        PAPER_GENERATED_RESOURCES_DIR.joinpath(benchmark.id).joinpath("keys.tex").write_text(output)

    @staticmethod
    def collect_quantile_data(benchmarks: List[Benchmark], vendors=None, clusters=config.clusters.values()) -> pd.DataFrame:
        if vendors is None:
            vendors = VendorDB.ANALYZED_VENDORS

        output_data = []
        for benchmark_index, benchmark in enumerate(benchmarks):
            for vendor_index, vendor in enumerate(vendors):
                for cluster_index, cluster in enumerate(clusters):
                    try:
                        data_query = SampleQuery(
                            benchmark=benchmark,
                            vendor=vendor,
                            cluster=cluster,
                            endpoint_type=EndpointType.PRIMARY_SLAVE,
                            normalize_time=False, timestamp_merge_append=False
                        )
                        data = data_query.run(Sample.SampleType.CLOCK_DIFF)
                    except NoDataError:
                        continue

                    unmodified_data = data.droplevel('endpoint_id').abs()
                    quantiles = [0.05, 0.5, 0.95]
                    quantile_values = unmodified_data.quantile(quantiles)

                    for quantile, value in zip(quantiles, quantile_values):
                        output_data.append({
                            'Benchmark': benchmark.name,
                            'Cluster': cluster.name,
                            'Vendor': vendor.name,
                            'Quantile': quantile,
                            'Value': value,
                            'Benchmark Index': benchmark_index,
                            'Cluster Index': cluster_index,
                            'Vendor Index': vendor_index,
                            'Benchmark Id': benchmark.id,
                            'Cluster Id': cluster.id,
                            'Vendor Id': vendor.id,
                        })
        return pd.DataFrame(output_data)
