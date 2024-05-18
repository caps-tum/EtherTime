import dataclasses
import logging
from datetime import timedelta
from typing import Tuple, List

import pandas as pd
from django.test import TestCase

from ptp_perf import config, util
from ptp_perf.charts.comparison_bar_element import ComparisonLineElement
from ptp_perf.charts.figure_container import FigureContainer, TimeseriesAxisContainer, AxisContainer
from ptp_perf.charts.timeseries_element import ScatterElement
from ptp_perf.constants import MEASUREMENTS_DIR, PAPER_GENERATED_RESOURCES_DIR
from ptp_perf.machine import Cluster
from ptp_perf.models import Sample, PTPEndpoint, PTPProfile
from ptp_perf.models.data_transform import DataTransform
from ptp_perf.models.endpoint import TimeNormalizationStrategy
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.models.exceptions import NoDataError
from ptp_perf.models.fault import Fault
from ptp_perf.models.sample_query import SampleQuery
from ptp_perf.profiles.benchmark import Benchmark
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.util import setup_logging
from ptp_perf.utilities import units
from ptp_perf.utilities.pandas_utilities import foreign_frame_column, frame_column
from ptp_perf.vendor.registry import VendorDB


class FaultComparisonCharts(TestCase):
    fault_split = pd.to_timedelta(11, unit='minutes')

    @classmethod
    def setUpClass(cls):
        setup_logging()
        super().setUpClass()

    def test_fault_scatter_comparison_chart(self):
        for benchmark, log_scale in [
            (BenchmarkDB.HARDWARE_FAULT_SLAVE, True),
            (BenchmarkDB.HARDWARE_FAULT_MASTER, True),
            (BenchmarkDB.HARDWARE_FAULT_SWITCH, False),
            (BenchmarkDB.HARDWARE_FAULT_MASTER_FAILOVER, True),
        ]:
            axis_containers = []
            clusters = [config.CLUSTER_PI, config.CLUSTER_PI5]
            if benchmark == BenchmarkDB.HARDWARE_FAULT_SWITCH or benchmark == BenchmarkDB.SOFTWARE_FAULT_SLAVE:
                clusters += [config.CLUSTER_PETALINUX, config.CLUSTER_TK1]

            for cluster in clusters:
                frame = DataTransform(
                    expansions=[PTPEndpoint.profile]
                ).run(
                    PTPEndpoint.objects.filter(
                        profile__cluster_id=cluster.id, profile__benchmark_id=benchmark.id,
                        profile__vendor_id__in=VendorDB.ANALYZED_VENDOR_IDS,
                    )
                )

                # Set nan return to normal == (never reconverged) to 4 minutes (at end of benchmark)
                # We label this manually later as never
                return_to_normal_column = frame_column(PTPEndpoint.fault_clock_diff_return_to_normal_time)
                timeout_value = 4
                frame[return_to_normal_column] = frame[return_to_normal_column].fillna(
                    timedelta(minutes=timeout_value)
                )

                axis_container = AxisContainer(
                    [ScatterElement(
                        data=frame,
                        column_x=return_to_normal_column,
                        column_y=frame_column(PTPEndpoint.fault_clock_diff_post_max),
                        column_hue=foreign_frame_column(PTPEndpoint.profile, PTPProfile.vendor_id),
                        column_style=foreign_frame_column(PTPEndpoint.profile, PTPProfile.vendor_id),
                        style_order=VendorDB.ANALYZED_VENDOR_IDS,
                    )],
                    title=f'{cluster}',
                    # xlabel='Resynchronization Time',
                    xticks=units.convert_all_units(units.NANOSECONDS_IN_SECOND, [0 * 60, 2 * 60, timeout_value * 60]),
                    xticklabels=["0 m", "2 m", "T/O"],
                    ylabel='Maximum Offset',
                    yticklabels_format_time=True,
                )
                self.configure_fault_ylog_axis(axis_container, include_nanoseconds=False)
                axis_containers.append(axis_container)
            # axis_containers[-1].legend = True
            figure = FigureContainer(
                axis_containers, title=benchmark.name, tight_layout=True,
                size=(4, 2) if benchmark != BenchmarkDB.HARDWARE_FAULT_SWITCH else (6, 2),
            )
            figure.plot()
            figure.save_default_locations("fault_scatter", benchmark)

    def test_hardware_fault_cluster_comparison_chart(self):
        for benchmark, log_scale in [
            (BenchmarkDB.HARDWARE_FAULT_SLAVE, True),
            (BenchmarkDB.HARDWARE_FAULT_MASTER, True),
            (BenchmarkDB.HARDWARE_FAULT_SWITCH, False),
            (BenchmarkDB.HARDWARE_FAULT_MASTER_FAILOVER, True),
        ]:
            axis_containers = []

            for cluster in [config.CLUSTER_PI, config.CLUSTER_PI5]:
                try:
                    frame, faults = self.prepare_multi_vendor_scatter_data(benchmark, cluster)
                    frame['exclude_column'] = frame['value'] >= timedelta(milliseconds=1).total_seconds()

                    # Mark the faults
                    max_fault_start = max(fault.start for fault in faults)
                    min_fault_end = min(fault.end for fault in faults)

                    xticks, xlabels = self.xticks_and_labels_from_fault(max_fault_start)
                    axis_container = TimeseriesAxisContainer(
                        title=cluster.name,
                        xticks=xticks,
                        xticklabels=xlabels,
                    ).add_elements(
                        *ComparisonLineElement(
                            data=frame,
                            marker='None',
                            x_coord_aggregate=timedelta(seconds=10),
                            x_coord_aggregate_exclude_column='exclude_column' if benchmark == BenchmarkDB.HARDWARE_FAULT_SLAVE else None,
                        ).configure_for_timeseries_input().split_data(self.fault_split)
                    )
                    if log_scale:
                        self.configure_fault_ylog_axis(axis_container)
                    axis_containers.append(axis_container)

                    if benchmark == BenchmarkDB.HARDWARE_FAULT_SLAVE and frame is not None:
                        max_outlier = frame.iloc[frame["value"].argmax()]
                        axis_container.annotate(
                            f"Offset: {units.format_time_offset(max_outlier.loc['value'])}$\\rightarrow$  ",
                            position=(
                                max_outlier.loc['timestamp'].total_seconds() * units.NANOSECONDS_IN_SECOND,
                                max_outlier.loc['value'],
                            ),
                            horizontalalignment='right', verticalalignment='center',
                        )

                    for boundary in [max_fault_start, min_fault_end]:
                        axis_container.add_boundary(boundary, linestyle='dotted', color='.7')

                except NoDataError:
                    logging.info(f"No data: {benchmark}")

            if len(axis_containers) > 0:
                chart = FigureContainer(axis_containers, tight_layout=True, size=(6, 3))
                chart.plot()

                chart.save(MEASUREMENTS_DIR.joinpath(f"{benchmark.id}_cluster_comparison.png"), make_parents=True)
                chart.save(PAPER_GENERATED_RESOURCES_DIR.joinpath(f"{benchmark.id}_cluster_comparison.pdf"),
                           make_parents=True)
            else:
                logging.info(f"No data for benchmark {benchmark}")

    def test_software_fault_peer_comparison(self):
        for cluster in [config.CLUSTER_PI, config.CLUSTER_PI5]:
            axis_containers = []
            try:
                benchmark = BenchmarkDB.SOFTWARE_FAULT_SLAVE
                frame_faulty, fault1 = self.prepare_multi_vendor_scatter_data(
                    benchmark, cluster
                )
                frame_faulty['exclude'] = frame_faulty['value'] > 30 * units.MICROSECONDS_TO_SECONDS
                frame_faultless, fault2 = self.prepare_multi_vendor_scatter_data(
                    benchmark, cluster, endpoint_type=EndpointType.SECONDARY_SLAVE
                )
                fault_start = max(fault.start for fault in fault1)
                # Have to use manual fault duration because the restart delay is not included in the log
                # min_fault_end = min(fault.end for fault in fault1)
                min_fault_end = fault_start + benchmark.fault_duration

                for vendor in VendorDB.ANALYZED_VENDORS:
                    axis_containers.append(
                        TimeseriesAxisContainer(
                            # title="Faulty Peer",
                            ylabel='Faulty Peer\nClock Offset',
                            yticks_interval=None,
                            ylimit_bottom=0,
                            ylimit_top=120 * units.MICROSECONDS_TO_SECONDS,
                            grid=False,
                        ).add_elements(
                            *ComparisonLineElement(
                                data=frame_faulty[frame_faulty['Vendor'] == vendor.id],
                                marker='None',
                                x_coord_aggregate=timedelta(seconds=5),
                                x_coord_aggregate_exclude_column='exclude',
                            ).configure_for_timeseries_input().split_data(self.fault_split)
                        ).add_boundary(
                            fault_start, linestyle='dotted', color='.7'
                        ).add_boundary(
                            min_fault_end, linestyle='dotted', color='.7'
                        )
                    )
                for vendor in VendorDB.ANALYZED_VENDORS:
                        xticks, xlabels = self.xticks_and_labels_from_fault(fault_start)
                        axis_containers.append(
                        TimeseriesAxisContainer(
                            # title="Faultless Peer",
                            ylabel='Faultless Peer\nClock Offset',
                            xticklabels_format_time=False,
                            xticks=xticks,
                            xticklabels=xlabels,
                            yticks_interval=None,
                            grid=False,
                        ).add_elements(
                            ComparisonLineElement(
                                data=frame_faultless[frame_faultless['Vendor'] == vendor.id],
                                marker='None',
                                x_coord_aggregate=timedelta(seconds=5),
                            ).configure_for_timeseries_input()
                        ).add_boundary(
                            fault_start, linestyle='dotted', color='.7'
                        ).add_boundary(
                            min_fault_end, linestyle='dotted', color='.7'
                        )
                    )
                chart = FigureContainer(
                    axis_containers,
                    tight_layout = True,
                    columns=4,
                    size=(5,3),
                )
                chart.plot()
                chart.save(MEASUREMENTS_DIR.joinpath(f"{benchmark.id}_{cluster.id}_peer_comparison.png"),
                           make_parents=True)
                chart.save(PAPER_GENERATED_RESOURCES_DIR.joinpath(f"{benchmark.id}_{cluster.id}_peer_comparison.pdf"),
                           make_parents=True)
            except NoDataError as e:
                logging.info(f"Missing data: {e}")

    def xticks_and_labels_from_fault(self, fault_start) -> Tuple[List[float], List[str]]:
        return units.convert_all_units(
            units.NANOSECONDS_IN_SECOND,
            [fault_start.total_seconds() - 120,
             fault_start.total_seconds(),
             fault_start.total_seconds() + 120]
        ), ["-2m", "0m", "2m"]

    def configure_fault_ylog_axis(self, axis_container: AxisContainer, include_nanoseconds: bool = True) -> None:
        yticks = [
            1 * units.NANOSECONDS_TO_SECONDS, 10 * units.NANOSECONDS_TO_SECONDS,
            100 * units.NANOSECONDS_TO_SECONDS,
        ] if include_nanoseconds else []
        yticks += [
            1 * units.MICROSECONDS_TO_SECONDS, 10 * units.MICROSECONDS_TO_SECONDS,
            100 * units.MICROSECONDS_TO_SECONDS,
            1 * units.MILLISECONDS_TO_SECONDS, 10 * units.MILLISECONDS_TO_SECONDS,
            100 * units.MILLISECONDS_TO_SECONDS,
            1, 60, 3600
        ]
        yticklabels = [
            "1 ns", "", "",
        ] if include_nanoseconds else []
        yticklabels += [
            "1 μs", "", "",
            "1 ms", "", "",
            "1 s", "1 m", "1 h",
        ]
        axis_container.ylog=True
        axis_container.yticks_interval=None
        axis_container.yminorticks=True
        axis_container.yminorticks_interval=None
        axis_container.yminorticks_fixed=[0.5 * ytick for ytick in yticks]
        axis_container.yticks=yticks
        axis_container.yticklabels=yticklabels
        axis_container.yticklabels_format_time=False
        axis_container.grid=False


    def prepare_multi_vendor_scatter_data(self,
                                          benchmark: Benchmark, cluster: Cluster,
                                          endpoint_type=EndpointType.PRIMARY_SLAVE,
                                          context: timedelta = timedelta(minutes=2.5)) -> Tuple[
        pd.DataFrame, List[Fault]]:
        query = SampleQuery(
            benchmark=benchmark,
            cluster=cluster,
            endpoint_type=endpoint_type,
            timestamp_merge_append=False,
            normalize_time=TimeNormalizationStrategy.PROFILE_START,
        )

        frame = query.run(Sample.SampleType.CLOCK_DIFF).reset_index()
        endpoints = {
            endpoint_id: PTPEndpoint.objects.get(id=endpoint_id)
            for endpoint_id in frame["endpoint_id"].unique().tolist()
        }
        profiles = set(endpoint.profile for endpoint in endpoints.values())
        faults = util.flat_map(lambda profile: Fault.from_profile(profile), profiles)

        vendors = {endpoint.id: endpoint.profile.vendor_id for endpoint in endpoints.values()}

        center_timestamp = benchmark.fault_interval + (benchmark.fault_duration / 2)
        frame = frame[
            (center_timestamp - context <= frame['timestamp'])
            & (frame['timestamp'] <= center_timestamp + context)
            ]
        frame['Vendor'] = frame["endpoint_id"].map(vendors)
        frame['value'] = frame['value'].abs()
        # frame['timestamp'] = frame['timestamp'] * units.NANOSECONDS_TO_SECONDS
        return frame, faults
