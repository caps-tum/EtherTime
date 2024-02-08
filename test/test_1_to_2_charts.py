from unittest import TestCase

import config
import constants
from machine import Machine
from profiles.base_profile import BaseProfile
from profiles.benchmark import Benchmark

CHART_DIRECTORY = constants.CHARTS_DIR.joinpath("1_to_2")
from charts.timeseries_chart_comparison import TimeSeriesChartComparison
from registry import resolve
from registry.benchmark_db import BenchmarkDB
from registry.resolve import ProfileDB
from vendor.registry import VendorDB


class Test1To2Charts(TestCase):
    profile_db = ProfileDB()

    def resolve_1_to_2(self, benchmark: Benchmark, machine: Machine, vendor_id: str) -> BaseProfile:
        return self.profile_db.resolve_most_recent(
            resolve.VALID_PROCESSED_PROFILE(),
            resolve.BY_BENCHMARK(benchmark),
            resolve.BY_MACHINE(machine),
            resolve.BY_VENDOR(VendorDB.get(vendor_id)),
        )

    def test_1_to_2_charts(self):
        vendors = [VendorDB.PTPD.id, VendorDB.LINUXPTP.id]

        # Compare base, and the 2 1-to-2-clients
        for vendor_id in vendors:
            baseline = self.profile_db.resolve_most_recent(
                resolve.VALID_PROCESSED_PROFILE(),
                resolve.BY_BENCHMARK(BenchmarkDB.BASE),
                resolve.BY_VENDOR(VendorDB.get(vendor_id))
            )
            profiles_1_to_2_clients = [
                self.resolve_1_to_2(BenchmarkDB.BASE_TWO_CLIENTS, config.MACHINE_RPI08, vendor_id),
                self.resolve_1_to_2(BenchmarkDB.BASE_TWO_CLIENTS, config.MACHINE_RPI07, vendor_id),
            ]
            profiles_software_fault_clients = [
                self.resolve_1_to_2(BenchmarkDB.SOFTWARE_FAULT, config.MACHINE_RPI08, vendor_id),
                self.resolve_1_to_2(BenchmarkDB.SOFTWARE_FAULT, config.MACHINE_RPI07, vendor_id),
            ]
            profiles_hardware_fault_clients = [
                self.resolve_1_to_2(BenchmarkDB.HARDWARE_FAULT_SWITCH, config.MACHINE_RPI08, vendor_id),
                self.resolve_1_to_2(BenchmarkDB.HARDWARE_FAULT_SWITCH, config.MACHINE_RPI07, vendor_id),
            ]

            chart = TimeSeriesChartComparison([
                baseline, *profiles_1_to_2_clients,
            ], labels=["Baseline", "1-to-2\nClient 1", "1-to-2\nClient 2"], x_label="Profile")
            chart.save(CHART_DIRECTORY.joinpath(f"1_to_2_clients_versus_base_{vendor_id}.png"), make_parent=True)

            # Software Fault
            if None not in profiles_software_fault_clients:
                chart = TimeSeriesChartComparison(
                    [
                        *profiles_1_to_2_clients, *profiles_software_fault_clients
                    ],
                    labels=["1-to-2\nClient 1", "1-to-2\nClient 2", "Software Fault\nNormal Client",
                            "Software Fault\nFaulty Client"],
                    x_label="Profile")
                chart.save(CHART_DIRECTORY.joinpath(f"software_fault_clients_comparison_{vendor_id}.png"), make_parent=True)

            # Hardware Fault
            if None not in profiles_hardware_fault_clients:
                chart = TimeSeriesChartComparison(
                    [
                        baseline, *profiles_1_to_2_clients, *profiles_hardware_fault_clients
                    ],
                    labels=["1-to-2\nClient 1", "1-to-2\nClient 2", "Hardware Fault\nNormal Client",
                            "Hardware Fault\nFaulty Client"],
                    x_label="Profile")
                chart.save(CHART_DIRECTORY.joinpath(f"hardware_fault_clients_comparison_{vendor_id}.png"), make_parent=True)
