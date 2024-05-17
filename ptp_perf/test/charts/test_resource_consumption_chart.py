from datetime import timedelta
from typing import Iterable

import pandas as pd
from django.test import TestCase

from ptp_perf import config
from ptp_perf.charts.comparison_bar_element import ComparisonBarElement, ComparisonLineElement
from ptp_perf.charts.figure_container import FigureContainer, AxisContainer, DataAxisContainer
from ptp_perf.constants import MEASUREMENTS_DIR, PAPER_GENERATED_RESOURCES_DIR
from ptp_perf.models import PTPEndpoint
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.vendor.registry import VendorDB


class ResourceConsumptionChartTest(TestCase):
    nodes_xticks = [2, 12]

    def test_create_chart(self):
        resource_consumption_masters = self.get_resource_consumption_endpoints([EndpointType.MASTER])
        chart = FigureContainer(
            axes_containers=[
                DataAxisContainer(
                    [
                        ComparisonBarElement(
                            data=pd.DataFrame([
                                ('ptpd', 840000),
                                ('linuxptp', 970000),
                                ('sptp', 21000000),
                                ('chrony', 12000000),
                            ], columns=['x', 'y']),
                            column_x='x', column_y='y', column_hue='x', order_vendors=True,
                        ),
                    ],
                    ylabel='Size', xticks=[],
                    title='ROM Usage',
                ),
                DataAxisContainer(
                    [
                        ComparisonLineElement(
                            data=pd.DataFrame([
                                # Duplicate items will become errorbars
                                # ('ptpd', 900000),
                                # ('ptpd', 1100000),
                                # ('linuxptp', 250000),
                                # ('linuxptp', 400000),
                                # ('sptp', 8000000),
                                # ('sptp', 16000000),
                                # ('chrony', 800000),
                                # ('chrony', 1000000),
                                (endpoint.benchmark.num_machines, endpoint.profile.vendor_id, endpoint.proc_mem_rss) for endpoint in resource_consumption_masters
                            ], columns=['x', 'hue', 'y']),
                            column_x='x', column_y='y', column_hue='hue',
                        )
                    ],
                    xlabel='Nodes', xticks=self.nodes_xticks,
                    ylabel='Resident Set Size',
                    title='RAM Usage',
                ),
                AxisContainer(
                    [
                        ComparisonLineElement(
                            data=pd.DataFrame([
                                # ('ptpd', 2.5),
                                # ('linuxptp', 2.5),
                                # ('chrony', 3.25),
                                # ('chrony', 6.25),
                                # ('sptp', 10),
                                (endpoint.benchmark.num_machines, endpoint.profile.vendor_id, endpoint.proc_cpu_percent * timedelta(hours=1).total_seconds())
                                for endpoint in resource_consumption_masters if endpoint.proc_cpu_percent is not None
                            ], columns=['x', 'hue', 'y']).sort_values(by='x'),
                            column_x='x', column_y='y', column_hue='hue',
                        )
                    ],
                    xlabel='Nodes', xticks=self.nodes_xticks,
                    ylabel='Activity / Hour',
                    yticklabels_format_engineering=True, yticklabels_format_engineering_unit='s',
                    title='CPU Time',
                ),
                DataAxisContainer(
                    [
                        ComparisonLineElement(
                            data=pd.DataFrame([
                                # ('sptp', 1100000),
                                (endpoint.benchmark.num_machines, endpoint.profile.vendor_id, endpoint.sys_net_ptp_iface_bytes_total / endpoint.resource_profile_length.total_seconds() * timedelta(hours=1).total_seconds())
                                for endpoint in resource_consumption_masters if endpoint.resource_profile_length is not None
                            ], columns=['x', 'hue', 'y']),
                            column_x='x', column_y='y', column_hue='hue',
                        )
                    ],
                    xlabel='Nodes', xticks=self.nodes_xticks,
                    ylabel='Data / Hour',
                    title='Data Rate',
                ),
                AxisContainer(
                    [
                        ComparisonLineElement(
                            data=pd.DataFrame([
                                # ('sptp', 1100000),
                                (endpoint.benchmark.num_machines, endpoint.profile.vendor_id, endpoint.sys_net_ptp_iface_packets_total / endpoint.resource_profile_length.total_seconds() * timedelta(hours=1).total_seconds())
                                for endpoint in resource_consumption_masters if endpoint.resource_profile_length is not None
                            ], columns=['x', 'hue', 'y']),
                            column_x='x', column_y='y', column_hue='hue',
                        )
                    ],
                    xlabel='Nodes',  xticks=self.nodes_xticks,
                    ylabel='Packets / Hour',
                    yticklabels_format_engineering=True,
                    title='Packet Rate',
                ),
            ],
            share_x=False,
            share_y=False,
            # w_space=1.5,
            tight_layout=True,
            size=(10,2),
        )
        chart.plot()
        chart.save_default_locations("summary_trend", "resource_consumption")

    def test_chart_quality_create(self):
        resource_consumption_slaves = self.get_resource_consumption_endpoints([EndpointType.PRIMARY_SLAVE, EndpointType.SECONDARY_SLAVE, EndpointType.TERTIARY_SLAVE])
        chart2 = FigureContainer(
            axes_containers=[
                AxisContainer(
                    [
                        ComparisonLineElement(
                            data=pd.DataFrame([
                                (
                                    endpoint.benchmark.num_machines,
                                    endpoint.profile.vendor_id,
                                    endpoint.clock_diff_median,
                                    # TODO: What about unknown clock diff?
                                )
                                for endpoint in resource_consumption_slaves
                            ], columns=['x', 'hue', 'y']),
                            column_x='x', column_y='y', column_hue='hue',
                            estimator='mean',
                        )
                    ],
                    xlabel="Nodes", xticks=self.nodes_xticks,
                    ylabel="Clock Diff",
                    yticklabels_format_time=True,
                ),
                AxisContainer(
                    [
                        ComparisonLineElement(
                            data=pd.DataFrame([
                                (
                                    endpoint.benchmark.num_machines,
                                    endpoint.profile.vendor_id,
                                    1 - endpoint.missing_samples_percent if endpoint.missing_samples_percent is not None else 0
                                )
                                for endpoint in resource_consumption_slaves
                            ], columns=['x', 'hue', 'y']),
                            column_x='x', column_y='y', column_hue='hue',
                            estimator='mean',
                        )
                    ],
                    xlabel="Nodes", xticks=self.nodes_xticks,
                    ylabel="Average Connectivity",
                    yticklabels_format_percent=True,
                )
            ],
            size=(8, 3),
            share_y=False,
            tight_layout=True,
        )
        chart2.plot()
        chart2.save_default_locations("summary_quality_trend", "resource_consumption")

    def get_resource_consumption_endpoints(self, endpoint_types: Iterable[EndpointType]):
        return PTPEndpoint.objects.filter(
            profile__is_processed=True, profile__is_corrupted=False,
            profile__benchmark_id__in=[benchmark.id for benchmark in BenchmarkDB.SCALABILITY_ALL],
            endpoint_type__in=endpoint_types,
            profile__cluster_id=config.CLUSTER_BIG_BAD.id,
            profile__vendor_id__in=VendorDB.ANALYZED_VENDOR_IDS,
        )