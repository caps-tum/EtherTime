import logging
from datetime import timedelta

import pandas as pd
from django.test import TestCase

from ptp_perf.machine import Cluster
from ptp_perf.models.exceptions import NoDataError
from ptp_perf.profiles.benchmark import Benchmark

from ptp_perf.charts.timeseries_element import ScatterElement
from ptp_perf.models.endpoint import TimeNormalizationStrategy
from ptp_perf.utilities import units
from ptp_perf import config
from ptp_perf.charts.figure_container import FigureContainer, TimeseriesAxisContainer
from ptp_perf.constants import MEASUREMENTS_DIR, PAPER_GENERATED_RESOURCES_DIR
from ptp_perf.models import Sample, PTPEndpoint
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.models.sample_query import SampleQuery
from ptp_perf.registry.benchmark_db import BenchmarkDB


class FaultComparisonCharts(TestCase):

    def test_hardware_fault_cluster_comparison_chart(self):
        benchmark = BenchmarkDB.HARDWARE_FAULT_SLAVE
        frame = self.prepare_multi_vendor_scatter_data(benchmark, config.CLUSTER_PI)
        frame_pi5 = self.prepare_multi_vendor_scatter_data(benchmark, config.CLUSTER_PI5)

        chart = FigureContainer([
            TimeseriesAxisContainer(
                title="Raspberry-Pi 4",
                ylog=True,
                yticks_interval=None,
                # yminorticks=True,
                # yminorticks_interval=None,
            ).add_elements(
                ScatterElement(data=frame).configure_for_timeseries_input()
            ),
            TimeseriesAxisContainer(
                title="Raspberry-Pi 5",
                ylog=True,
                yticks_interval=None,
                # yminorticks=True,
                # yminorticks_interval=None,
            ).add_elements(
                ScatterElement(data=frame_pi5).configure_for_timeseries_input()
            )
        ])
        chart.plot()
        chart.save(MEASUREMENTS_DIR.joinpath(f"{benchmark.id}_cluster_comparison.png"), make_parents=True)
        chart.save(PAPER_GENERATED_RESOURCES_DIR.joinpath(f"{benchmark.id}_cluster_comparison.pdf"), make_parents=True)

    def test_software_fault_peer_comparison(self):
        for cluster in [config.CLUSTER_PI, config.CLUSTER_PI5]:
            try:
                benchmark = BenchmarkDB.SOFTWARE_FAULT_SLAVE
                frame_faulty = self.prepare_multi_vendor_scatter_data(benchmark, cluster)
                frame_faultless = self.prepare_multi_vendor_scatter_data(benchmark, cluster, endpoint_type=EndpointType.SECONDARY_SLAVE)

                chart = FigureContainer([
                    TimeseriesAxisContainer(
                        title="Faulty Peer",
                    ).add_elements(
                        ScatterElement(data=frame_faulty).configure_for_timeseries_input()
                    ),
                    TimeseriesAxisContainer(
                        title="Faultless Peer",
                    ).add_elements(
                        ScatterElement(data=frame_faultless).configure_for_timeseries_input()
                    )
                ])
                chart.plot()
                chart.save(MEASUREMENTS_DIR.joinpath(f"{benchmark.id}_{cluster.id}_peer_comparison.png"), make_parents=True)
                chart.save(PAPER_GENERATED_RESOURCES_DIR.joinpath(f"{benchmark.id}_{cluster.id}_peer_comparison.pdf"), make_parents=True)
            except NoDataError:
                logging.info("Missing data.")

    def prepare_multi_vendor_scatter_data(self,
                                          benchmark: Benchmark, cluster: Cluster,
                                          endpoint_type=EndpointType.PRIMARY_SLAVE,
                                          context: timedelta = timedelta(minutes=2.5)) -> pd.DataFrame:
        query = SampleQuery(
            benchmark=benchmark,
            cluster=cluster,
            endpoint_type=endpoint_type,
            timestamp_merge_append=False,
            normalize_time=TimeNormalizationStrategy.PROFILE_START,
        )

        frame = query.run(Sample.SampleType.CLOCK_DIFF).reset_index()
        vendors = {endpoint_id: PTPEndpoint.objects.get(id=endpoint_id).profile.vendor_id
                   for endpoint_id in frame["endpoint_id"].unique().tolist()}

        center_timestamp = benchmark.fault_interval + (benchmark.fault_duration / 2)
        frame = frame[
            (center_timestamp - context <= frame['timestamp'])
            & (frame['timestamp'] <= center_timestamp + context)
        ]
        frame['Vendor'] = frame["endpoint_id"].map(vendors)
        frame['value'] = frame['value'].abs()
        frame['timestamp'] = frame['timestamp'] * units.NANOSECONDS_TO_SECONDS
        return frame
