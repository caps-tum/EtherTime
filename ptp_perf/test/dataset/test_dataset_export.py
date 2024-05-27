from django.test import TestCase

from ptp_perf import constants
from ptp_perf.registry.benchmark_db import BenchmarkDB


class DatasetExportTest(TestCase):

    def test_export_benchmark_overview(self):
        """Export a markdown file with an overview of all benchmarks including their description and key properties."""
        benchmarks = BenchmarkDB.all()
        markdown_output = ("""
            # Benchmark Database
            This document provides an overview of all benchmarks in the database, according to category.
            Each benchmark is described with its key properties and a brief explanation of what it measures. 
            For more detailed information, see the benchmark definition in the source code at `ptp_perf/registry/benchmark_db.py`. 
        """)


        for benchmark in benchmarks:
            markdown_output += (
                "### Benchmark: " + benchmark.name + "\n"
                f"_{benchmark.num_machines} machines, {benchmark.duration} duration._\n"
                + benchmark.description
            )

        constants.DATASET_DIR.joinpath("benchmark_overview.md").write_text(markdown_output)
