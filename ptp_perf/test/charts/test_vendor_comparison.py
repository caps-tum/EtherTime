import itertools
from typing import List

import numpy as np
import pandas as pd
from django.test import TestCase
from matplotlib import pyplot as plt
from matplotlib.patches import ConnectionPatch, ConnectionStyle

from ptp_perf import config
from ptp_perf.charts.chart_container import ChartContainer
from ptp_perf.charts.comparison_bar_element import ComparisonBarElement, ComparisonLineElement
from ptp_perf.charts.figure_container import FigureContainer, AxisContainer, TimeseriesAxisContainer, TimeAxisContainer, \
    TimeLogAxisContainer
from ptp_perf.config import CLUSTER_PI, CLUSTER_PI5
from ptp_perf.constants import MEASUREMENTS_DIR, PAPER_GENERATED_RESOURCES_DIR
from ptp_perf.machine import Cluster
from ptp_perf.models import BenchmarkSummary
from ptp_perf.profiles.base_profile import ProfileTags
from ptp_perf.profiles.benchmark import Benchmark
from ptp_perf.profiles.taxonomy import ResourceContentionComponent
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.util import str_join
from ptp_perf.utilities import units, colors
from ptp_perf.vendor.registry import VendorDB


class VendorComparisonCharts(TestCase):

    def test_load_chart(self):
        for cluster in [config.CLUSTER_PI, config.CLUSTER_PI5]:
            benchmarks = BenchmarkDB.all_by_tags(ProfileTags.COMPONENT_NET, ProfileTags.ISOLATION_UNPRIORITIZED)
            benchmarks = [benchmark for benchmark in benchmarks]
            benchmarks.append(BenchmarkDB.BASE)

            frame = self.collect_quantile_data(benchmarks, clusters=[cluster])
            frame['X'] = frame['Benchmark Id'].apply(lambda x: BenchmarkDB.get(x).artificial_load_network) / 1000
            frame.sort_values('X', inplace=True)
            print(frame)

            chart = FigureContainer(
                axes_containers=[
                    TimeLogAxisContainer(
                        [
                            ComparisonLineElement(
                                data=frame,
                                column_x='X',
                                column_y='Value',
                                column_hue='Vendor',
                                estimator='mean',
                            )
                        ],
                        title="Synchronization Quality with Unisolated Network Contention",
                        xlabel='Network Load',
                        xticklabels_format_percent=True,
                        ylabel=r"$\mathit{Mean}$ Clock Offset",
                    )
                ],
                tight_layout=True,
            )
            chart.plot()
            chart.save(MEASUREMENTS_DIR.joinpath("load").joinpath(f"unprioritized_trend_{cluster.id}.png"))
            chart.save(PAPER_GENERATED_RESOURCES_DIR.joinpath(f"net_unprioritized_trend_{cluster.id}.pdf"))

    def test_load_types_chart(self):
        for cluster in [config.CLUSTER_PI, config.CLUSTER_PI5]:
            benchmarks = BenchmarkDB.all_by_tags(
                ProfileTags.CATEGORY_LOAD,
                ProfileTags.ISOLATION_UNPRIORITIZED
            )
            benchmarks = [benchmark for benchmark in benchmarks if 'load_100' in benchmark.id]
            benchmarks.append(BenchmarkDB.BASE)

            frame = self.collect_quantile_data(benchmarks, clusters=[cluster])
            frame['X'] = frame['Benchmark'].str.replace('(Unprioritized|100\% Load)', '', regex=True).str.strip()
            # frame.sort_values('X', inplace=True)
            print(frame)

            chart = FigureContainer(
                axes_containers=[
                    TimeAxisContainer(
                        [
                            ComparisonBarElement(
                                data=frame,
                                column_x='X',
                                column_y='Value',
                                # column_hue='Vendor',
                                color_map=None,
                                estimator='mean',
                                color='0.5',
                            )
                        ],
                        title=f"Synchronization Quality by Type of Load ({cluster.name})",
                        xlabel='Load Type (Mean across all Boards)',
                        ylabel=r"$\mathit{Mean}$ Clock Offset",
                        yticks_interval=None,
                        grid=cluster.id == 'rpi-4',
                    )
                ],
                tight_layout=True,
                # size=(6,5),
            )
            chart.plot()
            plt.xticks(rotation=90)
            chart.save(MEASUREMENTS_DIR.joinpath("load").joinpath(f"load_types_{cluster.id}.png"))
            chart.save(PAPER_GENERATED_RESOURCES_DIR.joinpath("load").joinpath(f"load_types_{cluster.id}.pdf"))


    def test_vendor_chart(self):
        benchmark = BenchmarkDB.BASE
        frame = self.collect_quantile_data([benchmark])

        frame['X'] = (len(VendorDB.ANALYZED_VENDORS) + 0.5) * frame['Cluster Index'] + frame['Vendor Index']
        frame.sort_values('X', inplace=True)
        print(frame)

        frame_magnify = frame[
            (frame['Cluster'] == config.CLUSTER_PI5.name)
            | (frame['Cluster'] == config.CLUSTER_PETALINUX.name)
            | (frame['Cluster'] == config.CLUSTER_TK1.name)
        ]

        chart = FigureContainer(
            size=(6, 3),
            weights=[1.5, 1],
            w_space=0,
            share_x=False,
            share_y=False,
            tight_layout=True,
            axes_containers=[
                TimeAxisContainer(
                    [ComparisonBarElement(
                        data=frame,
                        column_x='X',
                        column_y='Value',
                        column_hue='Vendor'
                    )],
                    title="Baseline Performance by Vendor and Cluster",
                    xticks=[1.5, 6, 10.5, 15],
                    xticklabels=["R-Pi 4", "R-Pi 5", "Xilinx", "TK-1"],
                    ylabel='Median Clock Offset',
                    ylimit_top=45 * units.us,
                ),
                TimeAxisContainer(
                    [ComparisonBarElement(
                        data=frame_magnify,
                        column_x='X',
                        column_y='Value',
                        column_hue='Vendor',
                    )],
                    xticks=[6, 10.5, 15],
                    xticklabels=["R-Pi 5", "Xilinx", "TK-1"],
                    ylabel='',
                    ylimit_top=5.5 * units.us,
                    yminorticks=True,
                    yminorticklabels=True,
                    title="(Magnified)",
                )
            ],
        )
        chart.plot()
        ax1 = chart.axes_containers[0].axis
        ax2 = chart.axes_containers[1].axis
        boundary = 5 * units.us
        ax1.add_artist(
            ConnectionPatch(
                (1.0, boundary / ax1.get_ylim()[1]), (0.265, 0),
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
                linestyle='dashed', color='0.7',
                connectionstyle=ConnectionStyle('arc', angleA=0, angleB=180, armA=5, armB=5, rad=5),
            )
        )

        chart.save(MEASUREMENTS_DIR.joinpath(benchmark.id).joinpath("vendor_comparison.png"))
        chart.save(PAPER_GENERATED_RESOURCES_DIR.joinpath(benchmark.id).joinpath("vendor_comparison.pdf"))

    def test_isolation_comparison_charts(self):
        # Any isolation, Net/CPU component
        for component, tag, max_load_level in [
            (ResourceContentionComponent.NET, ProfileTags.COMPONENT_NET, 1000),
            (ResourceContentionComponent.CPU, ProfileTags.COMPONENT_CPU, 100)
        ]:
            benchmarks = BenchmarkDB.all_by_tags(ProfileTags.CATEGORY_LOAD, tag)
            # Only benchmarks with max load.
            benchmarks = [
                benchmark for benchmark in benchmarks
                if benchmark.artificial_load_network == max_load_level
                   or benchmark.artificial_load_cpu == max_load_level
            ]
            benchmarks.append(BenchmarkDB.BASE)

            self.create_isolation_chart(benchmarks, component=component, cluster=CLUSTER_PI)
            self.create_isolation_chart(benchmarks, component=component, cluster=CLUSTER_PI5)

    def create_isolation_chart(self, benchmarks, component: ResourceContentionComponent, cluster: Cluster):
        frame = self.collect_quantile_data(benchmarks, clusters=[cluster])
        frame["Benchmark"] = frame["Benchmark"].str.replace(f"{component} 100% Load", "").str.strip()
        frame["Benchmark and Vendor"] = frame["Benchmark"] + " " + frame["Vendor"]
        print(frame)
        print(f"Benchmark tags: {str_join(frame['Benchmark'].unique())}")
        figure = FigureContainer(
            axes_containers=[
                TimeLogAxisContainer(
                    data_elements=[
                        ComparisonBarElement(
                            data=frame,
                            column_x='Vendor',
                            column_y='Value',
                            column_hue='Benchmark',
                            hue_order=["Unprioritized", 'Prioritized', "Isolated", "Baseline"],
                            color_map=None,
                            # color_map=color_map,
                            # dodge=False,
                            # estimator='mean',
                        ),
                    ],
                    title=f"Isolation Mechanisms at 100% {component} Load",
                    xticks=[],
                    ylabel='Median Clock Offset',
                )
            ],
            # Aligns nicer without this.
            # tight_layout=True,
        )
        figure.plot()
        axis = figure.axes_containers[0].axis
        axis.set_ylim(bottom=axis.get_ylim()[0] * 0.85)
        labels = ["U"] * 4 + ["P"] * 4 + ["I"] * 4 + ["B"] * 4 + [""] * 4
        vendor_data = [
            (vendor.name,
            colors.adjust_lightness(ChartContainer.VENDOR_COLORS[vendor.id], 0.8 + 0.25 * shade) )
            for shade, vendor in itertools.product(range(4), VendorDB.ANALYZED_VENDORS)]
        for i , bar in enumerate(axis.patches):
            vendor_name, color = vendor_data[i % len(vendor_data)]
            bar.set_facecolor(color)
            axis.text(
                bar.get_x() + bar.get_width() / 2., axis.get_ylim()[0], labels[i],
                ha='center', va='bottom', weight='bold',
            )
            y_value = frame[
                # np.ones(len(frame), dtype=bool)
                (frame['Vendor'] == vendor_name)
                & (frame['Benchmark'].str.startswith(labels[i]))
            ]['Value'].mean()
            print(labels[i], y_value)
            if bar.get_width() > 0:
                axis.plot(bar.get_x() + bar.get_width() / 2, y_value, marker='o', color='0.9', markeredgecolor='0.2')
        figure.save_default_locations(f"isolation_comparison_{cluster.id}", f"load/{component.id}")

    def test_create_keys(self):
        data = BenchmarkSummary.objects.all()
        entries = []
        for item in data:
            prefix = f"    /ptpperf/{item.benchmark_id}/{item.cluster_id}/{item.vendor_id}"
            entries.append(
                f"{prefix}/count/.initial={item.count},"
            )
            entries.append(f"{prefix}/mean/.initial={item.clock_diff_mean},")
            for quantile, value in item.clock_quantiles().items():
                entries.append(f"{prefix}/q{int(quantile * 100)}/.initial={value},")
            for quantile, value in item.path_delay_quantiles().items():
                entries.append(f"{prefix}/pd/q{int(quantile * 100)}/.initial={value},")
            entries.append(f"{prefix}/fault/post_max/max/.initial={item.fault_clock_diff_post_max_max},")
            entries.append(f"{prefix}/fault/post_max/min/.initial={item.fault_clock_diff_post_max_min},")
            entries.append(f"{prefix}/fault/mid_max/max/.initial={item.fault_clock_diff_mid_max_max},")
            entries.append(f"{prefix}/fault/ratio/avg/.initial={item.fault_ratio_clock_diff_post_max_pre_median_mean},")
            entries.append(f"{prefix}/fault/secondary/post_max/max/.initial={item.secondary_fault_clock_diff_post_max_max},")
            entries.append(f"{prefix}/fault/secondary/post_max/min/.initial={item.secondary_fault_clock_diff_post_max_min},")
            entries.append(f"{prefix}/fault/secondary/ratio/avg/.initial={item.secondary_fault_ratio_clock_diff_post_max_pre_median_mean},")
            entries.append(f"{prefix}/sys/proc/cpu/.initial={item.proc_cpu_percent},")
        entries.sort()
        PAPER_GENERATED_RESOURCES_DIR.joinpath("summary_keys.tex").write_text(
            "\\ptpperfLoadKeys{\n"
            + str_join(entries, separator='\n')
            + "}"
        )

    @staticmethod
    def collect_quantile_data(benchmarks: List[Benchmark], vendors=None,
                              clusters=config.clusters.values()) -> pd.DataFrame:
        if vendors is None:
            vendors = VendorDB.ANALYZED_VENDORS

        output_data = []
        for benchmark_index, benchmark in enumerate(benchmarks):
            for vendor_index, vendor in enumerate(vendors):
                for cluster_index, cluster in enumerate(clusters):
                    try:
                        summary = BenchmarkSummary.get_query(benchmark, vendor, cluster).get()
                    except BenchmarkSummary.DoesNotExist:
                        continue

                    for quantile, value in summary.clock_quantiles(include_p99_and_max=False).items():
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
