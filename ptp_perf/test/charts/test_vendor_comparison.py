import itertools
from typing import List

import pandas as pd
from django.test import TestCase
from matplotlib.patches import ConnectionPatch, ConnectionStyle

from ptp_perf import config
from ptp_perf.charts.chart_container import ChartContainer
from ptp_perf.charts.comparison_bar_element import ComparisonBarElement, ComparisonLineElement
from ptp_perf.charts.figure_container import FigureContainer, AxisContainer, TimeseriesAxisContainer, TimeAxisContainer, \
    TimeLogAxisContainer
from ptp_perf.config import CLUSTER_PI
from ptp_perf.constants import MEASUREMENTS_DIR, PAPER_GENERATED_RESOURCES_DIR
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
                            )
                        ],
                        title="Unisolated Network Load",
                        xlabel='Network Load',
                        xticklabels_format_percent=True,
                    )
                ]
            )
            chart.plot()
            chart.save(MEASUREMENTS_DIR.joinpath("load").joinpath(f"unprioritized_trend_{cluster.id}.png"))
            chart.save(PAPER_GENERATED_RESOURCES_DIR.joinpath(f"net_unprioritized_trend_{cluster.id}.pdf"))

    def test_vendor_chart(self):
        benchmark = BenchmarkDB.BASE
        frame = self.collect_quantile_data([benchmark])

        frame['X'] = (len(VendorDB.ANALYZED_VENDORS) + 0.5) * frame['Cluster Index'] + frame['Vendor Index']
        frame.sort_values('X', inplace=True)
        print(frame)

        frame_magnify = frame[
            (frame['Cluster'] == config.CLUSTER_PI5.name)
            | (frame['Cluster'] == config.CLUSTER_PETALINUX.name)
        ]

        chart = FigureContainer(
            size=(8, 4),
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
                    xticks=[1.5, 6, 10.5, ],
                    xticklabels=["Raspberry-Pi 4", "Raspberry-Pi 5", "Petalinux", ],
                    ylimit_top=50 * units.us,
                ),
                TimeAxisContainer(
                    [ComparisonBarElement(
                        data=frame_magnify,
                        column_x='X',
                        column_y='Value',
                        column_hue='Vendor',
                    )],
                    xticks=[6, 10.5],
                    xticklabels=["Raspberry-Pi 5", "Petalinux"],
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
                (1.0, boundary / ax1.get_ylim()[1]), (0.333, 0),
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

    def test_vendor_resilience(self):
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

            self.create_isolation_chart(benchmarks, component=component)

    def create_isolation_chart(self, benchmarks, component: ResourceContentionComponent):
        frame = self.collect_quantile_data(benchmarks, clusters=[CLUSTER_PI])
        frame["Benchmark"] = frame["Benchmark"].str.replace(f"{component} 100% Load", "")
        frame["Benchmark and Vendor"] = frame["Benchmark"] + " " + frame["Vendor"]
        color_map = {
            f'{benchmark} {vendor_name}': ChartContainer.VENDOR_COLORS[vendor_name]
            for vendor_name, benchmark in itertools.product(frame["Vendor"].unique(), frame["Benchmark"].unique())
        }
        figure = FigureContainer(
            axes_containers=[
                TimeLogAxisContainer(
                    data_elements=[
                        ComparisonBarElement(
                            data=frame,
                            column_x='Vendor',
                            column_y='Value',
                            column_hue='Benchmark',
                            color_map=None,
                            # color_map=color_map,
                            # dodge=False,
                        )
                    ],
                    title=f"Isolation Mechanisms at 100% {component} Load",
                )
            ]
        )
        figure.plot()
        axis = figure.axes_containers[0].axis
        axis.set_ylim(bottom=axis.get_ylim()[0] * 0.85)
        labels = ["U"] * 4 + ["P"] * 4 + ["I"] * 4 + ["B"] * 4 + [""] * 4
        for i , bar in enumerate(axis.patches):
            vendor_colors = [ChartContainer.VENDOR_COLORS[vendor.id] for vendor in VendorDB.ANALYZED_VENDORS]
            vendor_shades = [colors.adjust_lightness(color, 0.8 + 0.25 * shade) for shade, color in itertools.product(range(4), vendor_colors)]
            bar.set_facecolor(vendor_shades[i % len(vendor_shades)])
            axis.text(
                bar.get_x() + bar.get_width() / 2., axis.get_ylim()[0], labels[i],
                ha='center', va='bottom', weight='bold',
            )
        figure.save(MEASUREMENTS_DIR.joinpath("load").joinpath(f"{component.id}_isolation_comparison.png"))
        figure.save(PAPER_GENERATED_RESOURCES_DIR.joinpath(f"{component.id}_isolation_comparison.pdf"))

    def test_create_keys(self):
        data = BenchmarkSummary.objects.all()
        entries = []
        for item in data:
            prefix = f"    /ptpperf/{item.benchmark_id}/{item.cluster_id}/{item.vendor_id}"
            entries.append(
                f"{prefix}/count/.initial={item.count},"
            )
            for quantile, value in item.clock_quantiles().items():
                entries.append(f"{prefix}/q{int(quantile * 100)}/.initial={value},")
            for quantile, value in item.path_delay_quantiles().items():
                entries.append(f"{prefix}/pd/q{int(quantile * 100)}/.initial={value},")
            entries.append(f"{prefix}/fault/post_max/max/.initial={item.fault_clock_diff_post_max_max},")
            entries.append(f"{prefix}/fault/post_max/min/.initial={item.fault_clock_diff_post_max_min},")
            entries.append(f"{prefix}/fault/ratio/avg/.initial={item.fault_ratio_clock_diff_post_max_pre_median_mean},")
            entries.append(f"{prefix}/fault/secondary/post_max/max/.initial={item.secondary_fault_clock_diff_post_max_max},")
            entries.append(f"{prefix}/fault/secondary/post_max/min/.initial={item.secondary_fault_clock_diff_post_max_min},")
            entries.append(f"{prefix}/fault/secondary/ratio/avg/.initial={item.secondary_fault_ratio_clock_diff_post_max_pre_median_mean},")
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

                    for quantile, value in summary.clock_quantiles().items():
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
