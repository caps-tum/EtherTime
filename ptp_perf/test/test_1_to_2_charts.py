import logging
import math
from datetime import timedelta
from typing import List
from unittest import TestCase

import pandas as pd

import config
from charts.comparison_chart import ComparisonChart
from charts.timeseries_chart import TimeseriesChart
from charts.timeseries_chart_versus import TimeSeriesChartVersus
from config import MACHINE_RPI08, MACHINE_RPI07
from ptp_perf.machine import Machine
from profiles.base_profile import BaseProfile
from profiles.benchmark import Benchmark
from registry import resolve
from registry.benchmark_db import BenchmarkDB
from registry.resolve import ProfileDB
from ptp_perf.util import unpack_one_value
from ptp_perf.vendor.registry import VendorDB
from ptp_perf.vendor.vendor import Vendor

SOFTWARE_FAULT_CHART_DIRECTORY = BenchmarkDB.SOFTWARE_FAULT.storage_base_path

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
            profiles_software_fault_clients = [
                self.resolve_1_to_2(BenchmarkDB.SOFTWARE_FAULT, config.MACHINE_RPI08, vendor),
                self.resolve_1_to_2(BenchmarkDB.SOFTWARE_FAULT, config.MACHINE_RPI07, vendor),
            ]
            profiles_hardware_fault_clients = [
                self.resolve_1_to_2(BenchmarkDB.HARDWARE_FAULT_SWITCH, config.MACHINE_RPI08, vendor),
                self.resolve_1_to_2(BenchmarkDB.HARDWARE_FAULT_SWITCH, config.MACHINE_RPI07, vendor),
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
                chart.save(BenchmarkDB.BASE_TWO_CLIENTS.storage_base_path.joinpath("clients_vs_base.png"), make_parent=True)

    def test_software_fault(self):
        for vendor in VendorDB.ANALYZED_VENDORS:
            # Software Fault
            try:
                non_fault_client_profile = unpack_one_value(self.resolve_1_to_2(BenchmarkDB.SOFTWARE_FAULT, MACHINE_RPI08, vendor, aggregated=True))
                fault_client_profile = unpack_one_value(self.resolve_1_to_2(BenchmarkDB.SOFTWARE_FAULT, MACHINE_RPI07, vendor, aggregated=True))
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
        for vendor in VendorDB.ANALYZED_VENDORS:
            for machine in [MACHINE_RPI07, MACHINE_RPI08]:
                fault_client_profile = self.profile_db.resolve_most_recent(
                    resolve.BY_VALID_BENCHMARK_AND_VENDOR(BenchmarkDB.SOFTWARE_FAULT, vendor), resolve.BY_MACHINE(machine)
                )
                if fault_client_profile is None:
                    continue

                segmentation_points = [
                    timedelta(seconds=x) for x in range(
                        math.floor(fault_client_profile.time_series.time_index.min().total_seconds()),
                        math.ceil(fault_client_profile.time_series.time_index.max().total_seconds()) + 60,
                        60,
                    )]
                segmented = fault_client_profile.time_series.segment(align=pd.Series(segmentation_points))
                print(segmented)
                chart = TimeseriesChart("Software Fault: The Wave")
                chart.add_clock_difference(segmented)
                chart.annotate(chart.axes[0], f"Number Faults = {len(segmentation_points)}")
                chart.save(SOFTWARE_FAULT_CHART_DIRECTORY.joinpath(f"software_fault_wave_{vendor}_{machine.id}.png"))

    # TODO: Code duplication
    def test_hardware_fault_wave(self):
        for vendor in VendorDB.ANALYZED_VENDORS:
            for machine in [MACHINE_RPI07, MACHINE_RPI08]:
                fault_client_profile = self.profile_db.resolve_most_recent(
                    resolve.BY_VALID_BENCHMARK_AND_VENDOR(BenchmarkDB.HARDWARE_FAULT_SWITCH, vendor), resolve.BY_MACHINE(machine)
                )
                if fault_client_profile is None:
                    continue

                segmentation_points = [
                    timedelta(seconds=x) for x in range(
                        math.floor(fault_client_profile.time_series.time_index.min().total_seconds()),
                        math.ceil(fault_client_profile.time_series.time_index.max().total_seconds()) + 60,
                        60,
                    )]
                segmented = fault_client_profile.time_series.segment(align=pd.Series(segmentation_points))
                print(segmented)
                chart = TimeseriesChart("Hardware Fault (Switch): The Wave")
                chart.add_clock_difference(segmented)
                chart.annotate(chart.axes[0], f"Number Faults = {len(segmentation_points)}")
                chart.save(SOFTWARE_FAULT_CHART_DIRECTORY.joinpath(f"hardware_fault_switch_wave_{vendor}_{machine.id}.png"))

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
        #     chart.save(CHART_DIRECTORY.joinpath(f"hardware_fault_clients_comparison_{vendor}.png"), make_parent=True)
        #
        #     chart = TimeSeriesChartVersus(
        #         profiles_1_to_2_clients[0], profiles_hardware_fault_clients[0]
        #     )
        #     chart.set_titles("No Faults", "Switch Hardware Fault")
        #     chart.save(CHART_DIRECTORY.joinpath(f"hardware_fault_clients_versus_{vendor}.png"), make_parent=True)
