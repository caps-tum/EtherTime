from datetime import timedelta
from unittest import TestCase

from ptp_perf.utilities.django_utilities import bootstrap_django_environment
bootstrap_django_environment()

from ptp_perf.charts.timeseries_element import ScatterElement
from ptp_perf.models.endpoint import TimeNormalizationStrategy
from ptp_perf.utilities import units
from ptp_perf import config
from ptp_perf.charts.figure_container import FigureContainer, AxisContainer
from ptp_perf.constants import MEASUREMENTS_DIR, PAPER_GENERATED_RESOURCES_DIR
from ptp_perf.models import Sample, PTPEndpoint
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.models.sample_query import SampleQuery
from ptp_perf.registry.benchmark_db import BenchmarkDB


class FaultComparisonCharts(TestCase):

    def test_timeseries_chart(self):
        for cluster in [config.CLUSTER_PI, config.CLUSTER_PI5]:
            query = SampleQuery(
                benchmark=BenchmarkDB.HARDWARE_FAULT_SWITCH,
                cluster=cluster,
                endpoint_type=EndpointType.PRIMARY_SLAVE,
                timestamp_merge_append=False,
                normalize_time=TimeNormalizationStrategy.PROFILE_START,
            )

            frame = query.run(Sample.SampleType.CLOCK_DIFF).reset_index()
            vendors = {endpoint_id: PTPEndpoint.objects.get(id=endpoint_id).profile.vendor_id
                       for endpoint_id in frame["endpoint_id"].unique().tolist()}
            frame = frame[frame['timestamp'] >= timedelta(minutes=5)]
            frame['Vendor'] = frame["endpoint_id"].map(vendors)
            frame['value'] = frame['value'].abs()
            frame['timestamp'] = frame['timestamp'] * units.NANOSECONDS_TO_SECONDS
            print(frame)

            chart = FigureContainer(
                axes_containers=[
                    AxisContainer(
                        [
                            ScatterElement(
                                data=frame,
                                column_x='timestamp',
                                column_y='value',
                                column_hue='Vendor',
                            ),
                        ],
                        title="Hardware Fault Switch",
                        xticklabels_format_time=True,
                        yticklabels_format_time=True,
                    )
                ]
            )
            chart.plot()
            chart.save(MEASUREMENTS_DIR.joinpath("fault").joinpath(f"hardware_fault_switch_{cluster.id}.png"),
                       make_parents=True)
            chart.save(PAPER_GENERATED_RESOURCES_DIR.joinpath(f"hardware_fault_switch_{cluster.id}.pdf"),
                       make_parents=True)
