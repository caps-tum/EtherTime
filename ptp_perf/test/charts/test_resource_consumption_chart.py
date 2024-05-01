import pandas as pd
from django.test import TestCase

from ptp_perf.charts.comparison_bar_element import ComparisonBarElement
from ptp_perf.charts.figure_container import FigureContainer, AxisContainer, DataAxisContainer
from ptp_perf.constants import MEASUREMENTS_DIR
from ptp_perf.models import PTPEndpoint
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.registry.benchmark_db import BenchmarkDB


class ResourceConsumptionChartTest(TestCase):

    def test_create_chart(self):
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
                            column_x='x', column_y='y', column_hue='x',
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
                                ('ptpd', 900000),
                                ('ptpd', 1100000),
                                ('linuxptp', 250000),
                                ('linuxptp', 400000),
                                ('sptp', 8000000),
                                ('sptp', 16000000),
                                ('chrony', 800000),
                                ('chrony', 1000000),
                            ], columns=['x', 'y']),
                            column_x='x', column_y='y', column_hue='x',
                        )
                    ],
                    ylabel='Resident Set Size', xticks=[],
                    title='RAM Usage',
                ),
                AxisContainer(
                    [
                        ComparisonBarElement(
                            data=pd.DataFrame([
                                ('ptpd', 2.5),
                                ('linuxptp', 2.5),
                                ('chrony', 3.25),
                                ('chrony', 6.25),
                                ('sptp', 10),
                            ], columns=['x', 'y']),
                            column_x='x', column_y='y', column_hue='x',
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
                                ('sptp', 1100000),
                            ], columns=['x', 'y']),
                            column_x='x', column_y='y', column_hue='x',
                        )
                    ],
                    ylabel='Data Transferred', xticks=[],
                    title='Network Usage',
                )
            ],
            share_y=False,
            # w_space=1.5,
            tight_layout=True,
            size=(6,3),
        )
        chart.plot()
        chart.save(MEASUREMENTS_DIR.joinpath("resource_consumption").joinpath("summary.png"), make_parents=True)

    def get_resource_consumption_endpoints(self):
        return PTPEndpoint.objects.filter(
            profile__benchmark_id=BenchmarkDB.RESOURCE_CONSUMPTION.id,
            endpoint_type__in=[EndpointType.MASTER, EndpointType.PRIMARY_SLAVE],
        )