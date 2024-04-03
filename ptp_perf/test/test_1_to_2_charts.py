import logging
import math
from datetime import timedelta
from typing import List
from unittest import TestCase

import pandas as pd
from matplotlib.patches import FancyArrowPatch

from ptp_perf.utilities import units
from ptp_perf.utilities.django_utilities import bootstrap_django_environment

bootstrap_django_environment()

from ptp_perf import config, constants
from ptp_perf.charts.comparison_chart import ComparisonChart
from ptp_perf.charts.timeseries_chart import TimeseriesChart
from ptp_perf.charts.timeseries_chart_versus import TimeSeriesChartVersus
from ptp_perf.config import MACHINE_RPI08, MACHINE_RPI07
from ptp_perf.machine import Machine
from ptp_perf.models.sample_query import SampleQuery, QueryPostProcessor
from ptp_perf.models.exceptions import NoDataError
from ptp_perf.profiles.base_profile import BaseProfile
from ptp_perf.profiles.benchmark import Benchmark
from ptp_perf.registry import resolve
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.registry.resolve import ProfileDB

from ptp_perf.models import PTPEndpoint, Sample
from ptp_perf.util import unpack_one_value
from ptp_perf.vendor.registry import VendorDB
from ptp_perf.vendor.vendor import Vendor

SOFTWARE_FAULT_CHART_DIRECTORY = BenchmarkDB.SOFTWARE_FAULT_SLAVE.storage_base_path

class Test1To2Charts(TestCase):
    profile_db = ProfileDB()

    def resolve_1_to_2(self, benchmark: Benchmark, machine: Machine, vendor: Vendor, aggregated: bool = False) -> List[BaseProfile]:
        return self.profile_db.resolve_all(
            resolve.BY_VALID_BENCHMARK_AND_VENDOR(benchmark, vendor) if not aggregated else resolve.BY_AGGREGATED_BENCHMARK_AND_VENDOR(benchmark, vendor),
            resolve.BY_MACHINE(machine),
        )

    def test_1_to_2_charts(self):
        vendors = VendorDB.ANALYZED_VENDORS

        # Compare base, and the 2 1-to-2-clients
        for vendor in vendors:
            baselines = self.profile_db.resolve_all(
                resolve.BY_VALID_BENCHMARK_AND_VENDOR(BenchmarkDB.BASE, vendor)
            )
            profiles_1_to_2_clients = [
                *self.resolve_1_to_2(BenchmarkDB.BASE_TWO_CLIENTS, config.MACHINE_RPI08, vendor),
                *self.resolve_1_to_2(BenchmarkDB.BASE_TWO_CLIENTS, config.MACHINE_RPI07, vendor),
            ]

            if None not in profiles_1_to_2_clients:
                chart_profiles = [*baselines, *profiles_1_to_2_clients]
                chart = ComparisonChart(
                    "Scalability: 1-to-2", chart_profiles,
                    x_axis_label="Profile",
                    use_bar=True,
                    include_p99=True, include_p99_separate_axis=True,
                )
                chart.plot_median_clock_diff_and_path_delay(
                    x_axis_values=lambda profile: 'Base' if profile.benchmark == BenchmarkDB.BASE else ('Client 1' if profile.machine_id == MACHINE_RPI08.id else 'Client 2'),
                )
                chart.save(BenchmarkDB.BASE_TWO_CLIENTS.storage_base_path.joinpath("clients_vs_base.png"), make_parents=True)

    def test_software_fault(self):
        for vendor in VendorDB.ANALYZED_VENDORS:
            # Software Fault
            try:
                query = SampleQuery(benchmark=BenchmarkDB.SOFTWARE_FAULT_SLAVE, machine=MACHINE_RPI08, vendor=vendor)
                result = query.run(Sample.SampleType.CLOCK_DIFF)
                print(result)

                non_fault_client_profile = unpack_one_value(self.resolve_1_to_2(BenchmarkDB.SOFTWARE_FAULT_SLAVE, MACHINE_RPI08, vendor, aggregated=True))
                fault_client_profile = unpack_one_value(self.resolve_1_to_2(BenchmarkDB.SOFTWARE_FAULT_SLAVE, MACHINE_RPI07, vendor, aggregated=True))
            except ValueError:
                logging.warning(f"Missing profiles for {vendor}")
                continue

            if non_fault_client_profile is None or fault_client_profile is None:
                self.skipTest("Missing profiles.")

            chart = TimeSeriesChartVersus(
                non_fault_client_profile, fault_client_profile,
            )
            chart.set_titles("Non-faulty client", "Software fault client")
            chart.save(SOFTWARE_FAULT_CHART_DIRECTORY.joinpath(f"software_fault_clients_comparison_{vendor}.png"))


    def test_software_fault_wave(self):
        for benchmark in [BenchmarkDB.SOFTWARE_FAULT_SLAVE, BenchmarkDB.HARDWARE_FAULT_SLAVE, BenchmarkDB.HARDWARE_FAULT_MASTER, BenchmarkDB.HARDWARE_FAULT_MASTER_FAILOVER, BenchmarkDB.HARDWARE_FAULT_SWITCH]:
            for vendor in VendorDB.ANALYZED_VENDORS:
                for machine in [MACHINE_RPI07, MACHINE_RPI08]:
                    try:
                        query = SampleQuery(benchmark, vendor, machine, normalize_time=False, timestamp_merge_append=False)
                        clock_diffs = query.run(Sample.SampleType.CLOCK_DIFF)

                        fault_location = benchmark.fault_machine
                        # On master failure, there is no convergence time to query.
                        fault_query = SampleQuery(benchmark, vendor, fault_location, normalize_time=False, timestamp_merge_append=False, converged_only=False, remove_clock_step=False)
                        fault_records = fault_query.run(Sample.SampleType.FAULT)

                        faults = fault_records.index.get_level_values("timestamp")[fault_records == 1]

                        aligned_data = QueryPostProcessor(clock_diffs).segment_and_align(faults, wrap=timedelta(minutes=2))
                        # aligned_data.index = aligned_data.index.droplevel("endpoint_id")
                        aligned_data.index = aligned_data.index.droplevel("cut_index")
                        aligned_data.sort_index(inplace=True)

                        chart = TimeseriesChart(
                            title=f"{benchmark}: {'Faulty Client' if machine.id == fault_location else 'Faultless Client'} ({machine})",
                            # ylimit_top=constants.RPI_CHART_DISPLAY_LIMIT
                        )
                        chart.add_clock_difference(aligned_data)

                        bound_left_side = aligned_data[aligned_data.index < timedelta(0)].abs().quantile(0.99)
                        bound_right_side = aligned_data[aligned_data.index >= timedelta(0)].abs().quantile(0.99)

                        arrow = FancyArrowPatch(
                            (5 * units.NANOSECONDS_IN_SECOND, bound_left_side),
                            (5 * units.NANOSECONDS_IN_SECOND, bound_right_side),
                            arrowstyle='<->'
                        )
                        chart.axes[0].add_patch(arrow)
                        # chart.axes[0].annotate(
                        #     f"$P_{{99}}$\n{bound_right_side / bound_left_side * 100 - 100:.0f}% difference",
                        #     xy=(0.5, 0.5), xycoords=arrow,
                        #     horizontalalignment='center', verticalalignment='center',
                        #     rotation=90,
                        # )
                        top_annotation = chart.axes[0].annotate(
                            f"{units.format_time_offset(bound_right_side)} $\\rightarrow$",
                            xy=(0.5, 1), xycoords=arrow,
                            horizontalalignment='center', verticalalignment='bottom',
                        )
                        chart.axes[0].annotate(
                            f"$\mathbf{{P_{{99}}}}$\n{bound_right_side / bound_left_side * 100 - 100:.0f}% difference",
                            xy=(0.5, 1), xycoords=top_annotation,
                            horizontalalignment='center', verticalalignment='bottom',
                            fontweight='bold',
                        )
                        chart.axes[0].annotate(
                            f"$\\leftarrow$ {units.format_time_offset(bound_left_side)}",
                            xy=(0.5, 0), xycoords=arrow,
                            horizontalalignment='center', verticalalignment='top',
                        )

                        chart.annotate(chart.axes[0], f"Number Faults = {len(faults)}", position=(0.05, 0.05), horizontalalignment='left', verticalalignment='bottom')
                        chart.save(benchmark.storage_base_path.joinpath(f"fault_wave_{vendor}_{machine.id}.png"), make_parents=True)
                    except NoDataError as e:
                        logging.warning(f"Missing data ({benchmark}, {vendor}, {machine}: {e}), skipping.")

    def test_hardware_fault(self):
        self.skipTest("Unupdated")
        # # Hardware Fault
        # if None not in profiles_hardware_fault_clients:
        #     chart = DistributionComparisonChart(
        #         [
        #             baselines, *profiles_1_to_2_clients, *profiles_hardware_fault_clients
        #         ],
        #         labels=["1-to-2\nClient 1", "1-to-2\nClient 2", "Hardware Fault\nNormal Client",
        #                 "Hardware Fault\nFaulty Client"],
        #         x_label="Profile")
        #     chart.save(CHART_DIRECTORY.joinpath(f"hardware_fault_clients_comparison_{vendor}.png"), make_parents=True)
        #
        #     chart = TimeSeriesChartVersus(
        #         profiles_1_to_2_clients[0], profiles_hardware_fault_clients[0]
        #     )
        #     chart.set_titles("No Faults", "Switch Hardware Fault")
        #     chart.save(CHART_DIRECTORY.joinpath(f"hardware_fault_clients_versus_{vendor}.png"), make_parents=True)
