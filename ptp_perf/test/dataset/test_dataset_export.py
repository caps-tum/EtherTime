from django.test import TestCase

from ptp_perf import constants
from ptp_perf.models import PTPProfile
from ptp_perf.registry.benchmark_db import BenchmarkDB


class DatasetExportTest(TestCase):

    def test_export_benchmark_overview(self):
        """Export a markdown file with an overview of all benchmarks including their description and key properties."""
        benchmarks = BenchmarkDB.all()
        markdown_output = (
            "# Benchmark Database\n\n"
            "This document provides an overview of all benchmarks in the database, according to category. "
            "Each benchmark is described with its key properties and a brief explanation of what it measures. "
            "For more detailed information, see the benchmark definition in the source code at `ptp_perf/registry/benchmark_db.py`.\n"
            "\n"
        )


        for benchmark in benchmarks:
            markdown_output += (
                benchmark.summary_markdown() + "\n"
            )

        constants.DATASET_DIR.joinpath("benchmark_overview.md").write_text(markdown_output)

    def test_export_data(self):
        """Fetch PTPProfiles, related PTPEndpoints and write them to JSON."""
        profiles = PTPProfile.objects.filter(benchmark_id=BenchmarkDB.BASE.id).prefetch_related(
            "ptpendpoint_set",
            # "ptpendpoint_set__sample_set", "ptpendpoint_set__logrecord_set",
        ).all()[:10]
        for profile in profiles:
            profile: PTPProfile
            json = profile.export_as_json()
            output_file = constants.DATASET_DIR.joinpath("profiles").joinpath(f"{profile.id}.json")
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json)
            print(f"Exported profile {profile.id} to {output_file}.")
