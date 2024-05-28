import gzip

from django.test import TestCase

from ptp_perf import constants
from ptp_perf.models import PTPProfile, PTPEndpoint
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.utilities.django_utilities import format_custom_field


class DatasetExportTest(TestCase):

    def test_export_benchmark_overview(self):
        """Export a markdown file with an overview of all benchmarks including their description and key properties."""
        benchmarks = BenchmarkDB.all()
        markdown_output = (
            "# Benchmark Database\n\n"
            "This document provides an overview of all benchmarks in the database, according to category. "
            "Each benchmark is described with its key properties and a brief explanation of what it measures. "
            "We also include a table with summary statistics of the profiles we collected for each benchmark (sorted by median clock offset). "
            "For more detailed information, see the benchmark definition in the source code at `ptp_perf/registry/benchmark_db.py`.\n"
            "\n"
        )


        for benchmark in benchmarks:
            markdown_output += (
                f"{benchmark.summary_markdown()}\n\n"
                f"| Profile id | Benchmark | Vendor | Cluster | Machine | Endpoint type | Clock diff median | Clock diff p95 | Path delay median | Missing samples percent | Converged percentage | Convergence duration | Convergence max offset | Convergence rate |\n"
                f"|------------|-----------|--------|---------|---------|---------------|-------------------|----------------|-------------------|-------------------------|----------------------|----------------------|------------------------|------------------|\n"
            )
            for endpoint in PTPEndpoint.objects.filter(
                profile__benchmark_id=benchmark.id, profile__is_processed=True, profile__is_corrupted=False,
                endpoint_type__contains="SLAVE",
            ):
                markdown_output += (
                    f"| {endpoint.profile_id} | {endpoint.profile.benchmark} | {endpoint.profile.vendor} | {endpoint.profile.cluster} | {endpoint.machine} | {endpoint.endpoint_type} "
                    f"| {format_custom_field(endpoint, 'clock_diff_median')} | {format_custom_field(endpoint, 'clock_diff_p95')} | {format_custom_field(endpoint, 'path_delay_median')}"
                    f"| {format_custom_field(endpoint, 'missing_samples_percent')} | {format_custom_field(endpoint, 'converged_percentage')} | {format_custom_field(endpoint, 'convergence_duration')} | {format_custom_field(endpoint, 'convergence_max_offset')} | {format_custom_field(endpoint, 'convergence_rate')} |\n"
                )

        constants.DATASET_DIR.joinpath("benchmark_overview.md").write_text(markdown_output)

    def test_export_data(self):
        """Fetch PTPProfiles, related PTPEndpoints and write them to JSON."""
        benchmarks = BenchmarkDB.all()
        for benchmark_index, benchmark in enumerate(benchmarks):
            print(f"Now exporting benchmark {benchmark_index+1}/{len(benchmarks)}: {benchmark}")
            profiles = PTPProfile.objects.filter(benchmark_id=benchmark.id).prefetch_related(
                "ptpendpoint_set",
                # "ptpendpoint_set__sample_set", "ptpendpoint_set__logrecord_set",
            )
            count = profiles.count()
            for index, profile in enumerate(profiles):
                profile: PTPProfile
                output_file = constants.DATASET_DIR.joinpath("profiles").joinpath(profile.benchmark.id).joinpath(f"{profile.vendor_id}_{profile.id}.json.gz")
                if output_file.exists():
                    print("Skipping existing file", output_file)
                    continue
                json = profile.export_as_json()
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with gzip.open(output_file, "wt") as output_stream:
                    output_stream.write(json)
                print(f"Exported profile {index+1}/{count} of benchmark {benchmark} to {output_file}.")
