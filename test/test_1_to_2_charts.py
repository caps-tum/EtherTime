from unittest import TestCase

import config
import constants
from charts.timeseries_chart_versus import TimeSeriesChartVersus
from machine import Machine
from profiles.base_profile import BaseProfile
from profiles.benchmark import Benchmark
from vendor.vendor import Vendor

CHART_DIRECTORY = constants.CHARTS_DIR.joinpath("1_to_2")
from charts.timeseries_chart_comparison import TimeSeriesChartComparison
from registry import resolve
from registry.benchmark_db import BenchmarkDB
from registry.resolve import ProfileDB
from vendor.registry import VendorDB


class Test1To2Charts(TestCase):
    profile_db = ProfileDB()

    def resolve_1_to_2(self, benchmark: Benchmark, machine: Machine, vendor: Vendor) -> BaseProfile:
        return self.profile_db.resolve_most_recent(
            resolve.BY_VALID_BENCHMARK_AND_VENDOR(benchmark, vendor),
            resolve.BY_MACHINE(machine),
        )

    def test_1_to_2_charts(self):
        vendors = VendorDB.ANALYZED_VENDORS

        # Compare base, and the 2 1-to-2-clients
        for vendor in vendors:
            baseline = self.profile_db.resolve_most_recent(
                resolve.BY_VALID_BENCHMARK_AND_VENDOR(BenchmarkDB.BASE, vendor)
            )
            profiles_1_to_2_clients = [
                self.resolve_1_to_2(BenchmarkDB.BASE_TWO_CLIENTS, config.MACHINE_RPI08, vendor),
                self.resolve_1_to_2(BenchmarkDB.BASE_TWO_CLIENTS, config.MACHINE_RPI07, vendor),
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
                chart = TimeSeriesChartComparison([
                    baseline, *profiles_1_to_2_clients,
                ], labels=["Baseline", "1-to-2\nClient 1", "1-to-2\nClient 2"], x_label="Profile")
                chart.save(CHART_DIRECTORY.joinpath(f"1_to_2_clients_versus_base_{vendor}.png"), make_parent=True)

            # Software Fault
            if None not in profiles_software_fault_clients:
                chart = TimeSeriesChartComparison(
                    [
                        *profiles_1_to_2_clients, *profiles_software_fault_clients
                    ],
                    labels=["1-to-2\nClient 1", "1-to-2\nClient 2", "Software Fault\nNormal Client",
                            "Software Fault\nFaulty Client"],
                    x_label="Profile")
                chart.save(CHART_DIRECTORY.joinpath(f"software_fault_clients_comparison_{vendor}.png"), make_parent=True)

                chart = TimeSeriesChartVersus(
                    profiles_1_to_2_clients[0], profiles_software_fault_clients[0]
                )
                chart.set_titles("No Faults", "Software Faults (Non-Faulty Client)")
                chart.save(CHART_DIRECTORY.joinpath(f"software_fault_clients_versus_{vendor}.png"), make_parent=True)

            # Hardware Fault
            if None not in profiles_hardware_fault_clients:
                chart = TimeSeriesChartComparison(
                    [
                        baseline, *profiles_1_to_2_clients, *profiles_hardware_fault_clients
                    ],
                    labels=["1-to-2\nClient 1", "1-to-2\nClient 2", "Hardware Fault\nNormal Client",
                            "Hardware Fault\nFaulty Client"],
                    x_label="Profile")
                chart.save(CHART_DIRECTORY.joinpath(f"hardware_fault_clients_comparison_{vendor}.png"), make_parent=True)

                chart = TimeSeriesChartVersus(
                    profiles_1_to_2_clients[0], profiles_hardware_fault_clients[0]
                )
                chart.set_titles("No Faults", "Switch Hardware Fault")
                chart.save(CHART_DIRECTORY.joinpath(f"hardware_fault_clients_versus_{vendor}.png"), make_parent=True)
