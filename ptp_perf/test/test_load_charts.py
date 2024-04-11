from unittest import TestCase

from ptp_perf.utilities.django_utilities import bootstrap_django_environment

bootstrap_django_environment()

from ptp_perf import constants
from ptp_perf.models.profile_query import ProfileQuery
from ptp_perf.charts.comparison_chart import ComparisonChart
from ptp_perf.charts.distribution_comparison_chart import DistributionComparisonChart
from ptp_perf.charts.timeseries_chart_versus import TimeSeriesChartVersus
from ptp_perf.profiles.base_profile import ProfileTags
from ptp_perf.registry import resolve
from ptp_perf.registry.benchmark_db import BenchmarkDB, ResourceContentionType, ResourceContentionComponent
from ptp_perf.vendor.registry import VendorDB
from ptp_perf.models.sample_query import SampleQuery

LOAD_CHART_DIRECTORY = constants.CHARTS_DIR.joinpath("load")


class TestLoadCharts(TestCase):
    def test_create(self):
        profiles = ProfileQuery(
            tags=[ProfileTags.CATEGORY_LOAD, ProfileTags.COMPONENT_NET, ProfileTags.ISOLATION_UNPRIORITIZED]
        ).run()

        # Also include the baseline
        profiles += ProfileQuery(
            benchmark=BenchmarkDB.BASE
        ).run()

        profiles.sort(key=lambda profile: profile.benchmark.artificial_load_network)
        endpoints = [profile.endpoint_primary_slave for profile in profiles]

        chart = ComparisonChart(
            "Unisolated Network Load", endpoints,
            x_axis_label="Network Utilization"
        )
        chart.plot_median_clock_diff_and_path_delay(
            lambda endpoint: endpoint.profile.benchmark.artificial_load_network / 10,  # GBit/s to %
        )
        chart.save(LOAD_CHART_DIRECTORY.joinpath("load_network_unisolated.png"), make_parents=True)

        chart = ComparisonChart(
            "Unisolated Network Load", endpoints,
            x_axis_label = "Network Utilization",
            include_p99=True,
        )
        chart.plot_median_clock_diff_and_path_delay(
            lambda profile: profile.benchmark.artificial_load_network / 10,  # GBit/s to %
        )
        chart.save(LOAD_CHART_DIRECTORY.joinpath("load_network_unisolated_p99.png"), make_parents=True)

        # Show some distribution trends for each vendor
        vendors = set(profile.vendor.id for profile in profiles)
        for vendor_id in vendors:
            filtered_profiles = [profile for profile in profiles if profile.vendor.id == vendor_id]
            # Distribution chart
            chart = DistributionComparisonChart(
                filtered_profiles,
                labels=[f"{profile.benchmark.artificial_load_network / 10:.0f}%" for profile in filtered_profiles],
                x_label="Network Load",
            )
            # chart.axes.set_yscale('log')
            chart.save(LOAD_CHART_DIRECTORY.joinpath(f"load_network_unisolated_distributions_{vendor_id}.png"), make_parents=True)

        # Compare unisolated to isolated
        for vendor_id in vendors:
            chart = TimeSeriesChartVersus(
                profile_db.resolve_most_recent(
                    resolve.VALID_PROCESSED_PROFILE(),
                    resolve.BY_BENCHMARK(BenchmarkDB.BASE),
                    resolve.BY_VENDOR(VendorDB.get(vendor_id))
                ),
                profile_db.resolve_most_recent(
                    resolve.VALID_PROCESSED_PROFILE(),
                    resolve.BY_BENCHMARK(BenchmarkDB.resource_contention(ResourceContentionComponent.NET, ResourceContentionType.UNPRIORITIZED, 100)),
                    resolve.BY_VENDOR(VendorDB.get(vendor_id)),
                )
            )
            chart.save(LOAD_CHART_DIRECTORY.joinpath(f"load_network_unisolated_versus_{vendor_id}.png"))

    def test_unisolated_prioritized_isolated_comparison(self):
        # Compare base, unisolated, prioritized, (eventually isolated)
        profile_db = ProfileDB()
        for vendor in VendorDB.ANALYZED_VENDORS:
            profiles = [
                profile_db.resolve_most_recent(
                    resolve.BY_AGGREGATED_BENCHMARK_AND_VENDOR(BenchmarkDB.BASE, vendor),
                ),
                profile_db.resolve_most_recent(
                    resolve.BY_AGGREGATED_BENCHMARK_AND_VENDOR(BenchmarkDB.resource_contention(ResourceContentionComponent.NET, ResourceContentionType.UNPRIORITIZED, 100), vendor),
                ),
                profile_db.resolve_most_recent(
                    resolve.BY_AGGREGATED_BENCHMARK_AND_VENDOR(BenchmarkDB.resource_contention(ResourceContentionComponent.NET, ResourceContentionType.PRIORITIZED, 100), vendor),
                ),
            ]
            if None in profiles:
                self.skipTest("Missing comparison profiles.")

            chart = DistributionComparisonChart(profiles, labels=["Baseline", "Unprioritized (100% load)", "Prioritized (100% load)"], x_label="Profile")

            chart.save(LOAD_CHART_DIRECTORY.joinpath(f"load_network_versus_base_{vendor}.png"))

    def test_baseline_versus_1_percent_comparison(self):
        # Compare baseline to 1% additional load
        for vendor in VendorDB.ANALYZED_VENDORS:
            baseline = SampleQuery(benchmark=BenchmarkDB.BASE, vendor=vendor)
            load_1_percent = SampleQuery(
                benchmark=BenchmarkDB.resource_contention(ResourceContentionComponent.NET, ResourceContentionType.UNPRIORITIZED, 1),
                vendor=vendor
            )

            if None in [baseline, load_1_percent]:
                self.skipTest("Missing profiles.")

            chart = TimeSeriesChartVersus(
                baseline,
                load_1_percent,
            )

            chart.save(LOAD_CHART_DIRECTORY.joinpath(f"load_base_vs_1_percent_{vendor}.png"))

    def test_generate_markdown_document(self):
        output_dir = constants.DATA_DIR.joinpath("profiles").joinpath("load").joinpath("net_unprioritized")

        document = """# Network Load Contention Test (Unprioritized)\n"""

        profiles = ProfileQuery(
            tags=[ProfileTags.CATEGORY_LOAD, ProfileTags.COMPONENT_NET, ProfileTags.ISOLATION_UNPRIORITIZED]
        ).run()
        for aggregated_profile in profiles:
            picture = aggregated_profile.file_path.parent.parent.joinpath("timeseries").joinpath("rpi08-path-delay.png").relative_to(output_dir)
            document += f"![{aggregated_profile.id}]({picture})\n"

        output_dir.joinpath("unprioritized-load.md").write_text(document)
