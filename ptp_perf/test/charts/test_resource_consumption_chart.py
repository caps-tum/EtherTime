from datetime import timedelta

import pandas as pd
from django.test import TestCase

from ptp_perf.charts.comparison_bar_element import ComparisonBarElement
from ptp_perf.charts.figure_container import FigureContainer, AxisContainer, DataAxisContainer
from ptp_perf.constants import MEASUREMENTS_DIR, PAPER_GENERATED_RESOURCES_DIR
from ptp_perf.models import PTPEndpoint
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.registry.benchmark_db import BenchmarkDB


class ResourceConsumptionChartTest(TestCase):

    def test_create_chart(self):
        resource_consumption_endpoints = self.get_resource_consumption_endpoints()
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
                        ComparisonBarElement(
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
                                (endpoint.profile.vendor_id, endpoint.proc_mem_rss) for endpoint in resource_consumption_endpoints
                            ], columns=['x', 'y']),
                            column_x='x', column_y='y', column_hue='x', order_vendors=True,
                        )
                    ],
                    ylabel='Resident Set Size', xticks=[],
                    title='RAM Usage',
                ),
                AxisContainer(
                    [
                        ComparisonBarElement(
                            data=pd.DataFrame([
                                # ('ptpd', 2.5),
                                # ('linuxptp', 2.5),
                                # ('chrony', 3.25),
                                # ('chrony', 6.25),
                                # ('sptp', 10),
                                (endpoint.profile.vendor_id, endpoint.proc_cpu_percent * timedelta(hours=1).total_seconds())
                                for endpoint in resource_consumption_endpoints
                            ], columns=['x', 'y']).sort_values(by='x'),
                            column_x='x', column_y='y', column_hue='x', order_vendors=True,
                        )
                    ],
                    ylabel='Activity / Hour', xticks=[],
                    yticklabels_format_engineering=True, yticklabels_format_engineering_unit='s',
                    title='CPU Time',
                ),
                DataAxisContainer(
                    [
                        ComparisonBarElement(
                            data=pd.DataFrame([
                                # ('sptp', 1100000),
                                (endpoint.profile.vendor_id, endpoint.sys_net_ptp_iface_bytes_total / endpoint.resource_profile_length.total_seconds() * timedelta(hours=1).total_seconds())
                                for endpoint in resource_consumption_endpoints
                            ], columns=['x', 'y']),
                            column_x='x', column_y='y', column_hue='x', order_vendors=True,
                        )
                    ],
                    ylabel='Data / Hour', xticks=[],
                    title='Data Rate',
                ),
                AxisContainer(
                    [
                        ComparisonBarElement(
                            data=pd.DataFrame([
                                # ('sptp', 1100000),
                                (endpoint.profile.vendor_id, endpoint.sys_net_ptp_iface_packets_total / endpoint.resource_profile_length.total_seconds() * timedelta(hours=1).total_seconds())
                                for endpoint in resource_consumption_endpoints
                            ], columns=['x', 'y']),
                            column_x='x', column_y='y', column_hue='x', order_vendors=True,
                        )
                    ],
                    ylabel='Packets / Hour', xticks=[],
                    yticklabels_format_engineering=True,
                    title='Packet Rate',
                ),
            ],
            share_y=False,
            # w_space=1.5,
            tight_layout=True,
            size=(10,2),
        )
        chart.plot()
        chart.save(MEASUREMENTS_DIR.joinpath("resource_consumption").joinpath("summary.png"), make_parents=True)
        chart.save(PAPER_GENERATED_RESOURCES_DIR.joinpath("resource_consumption").joinpath("summary.pdf"), make_parents=True)

    def get_resource_consumption_endpoints(self):
        return PTPEndpoint.objects.filter(
            profile__benchmark_id=BenchmarkDB.RESOURCE_CONSUMPTION.id,
            endpoint_type__in=[EndpointType.MASTER, EndpointType.PRIMARY_SLAVE],
        )