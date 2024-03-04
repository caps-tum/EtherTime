from unittest import TestCase

import config
from charts.comparison_chart import ComparisonChart
from registry import resolve
from registry.benchmark_db import BenchmarkDB
from registry.resolve import ProfileDB


class KeyMetricVarianceCharts(TestCase):

    def test_chart(self):
        for benchmark in BenchmarkDB().all():
            for machine in config.machines.values():
                profiles = ProfileDB().resolve_all(
                    resolve.VALID_PROCESSED_PROFILE(), resolve.BY_BENCHMARK(benchmark), resolve.BY_MACHINE(machine)
                )
                if len(profiles) == 0:
                    continue

                profiles.sort(key=lambda profile: profile.vendor.id)

                comparison_chart = ComparisonChart(
                    title=f"Variance of Key Metrics ({benchmark.name} {machine.id})",
                    profiles=profiles,
                    x_axis_label="Profile",
                    use_bar=True,
                    include_p99=True, include_p99_separate_axis=True,
                    include_annotate_range=True,
                )
                comparison_chart.plot_median_clock_diff_and_path_delay(
                    x_axis_values=lambda profile: profiles.index(profile),
                )

                comparison_chart.save(benchmark.storage_base_path.joinpath(f"key_metric_variance_{machine.id}.png"))
