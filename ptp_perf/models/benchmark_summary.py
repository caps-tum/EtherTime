from typing import Dict

from django.db import models

from ptp_perf.machine import Cluster
from ptp_perf.models import Sample
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.models.sample_query import SampleQuery
from ptp_perf.profiles.benchmark import Benchmark
from ptp_perf.vendor.vendor import Vendor


class BenchmarkSummary(models.Model):
    id = models.BigAutoField(primary_key=True)
    benchmark_id = models.CharField(max_length=255)
    vendor_id = models.CharField(max_length=255)
    cluster_id = models.CharField(max_length=255)

    count = models.IntegerField()

    # Summary statistics
    clock_diff_median = models.FloatField(null=True)
    clock_diff_p05 = models.FloatField(null=True)
    clock_diff_p95 = models.FloatField(null=True)
    path_delay_median = models.FloatField(null=True)
    path_delay_p05 = models.FloatField(null=True)
    path_delay_p95 = models.FloatField(null=True)
    path_delay_std = models.FloatField(null=True)

    @staticmethod
    def create(benchmark: Benchmark, vendor: Vendor, cluster: Cluster, force_update: bool = False):
        query_existing_objects = BenchmarkSummary.get_query(benchmark, vendor, cluster)
        if query_existing_objects.count() > 0:
            if force_update:
                query_existing_objects.delete()
            else:
                return

        data_query = SampleQuery(
            benchmark=benchmark,
            vendor=vendor,
            cluster=cluster,
            endpoint_type=EndpointType.PRIMARY_SLAVE,
            normalize_time=False, timestamp_merge_append=False
        )

        quantiles = [0.05, 0.5, 0.95]

        clock_data = data_query.run(Sample.SampleType.CLOCK_DIFF)
        count = len(clock_data.index.get_level_values("endpoint_id").unique())
        clock_data = clock_data.droplevel('endpoint_id').abs()
        clock_quantiles = clock_data.quantile(quantiles).values

        path_delay_data = data_query.run(Sample.SampleType.PATH_DELAY)
        path_delay_data = path_delay_data.droplevel('endpoint_id')
        path_delay_quantiles = path_delay_data.quantile(quantiles).values

        print(f'{benchmark} {vendor} {cluster}: '
              f'Clock quantiles: {clock_quantiles}, path delay quantiles: {path_delay_quantiles}')

        instance = BenchmarkSummary(
            benchmark_id=benchmark.id,
            vendor_id=vendor.id,
            cluster_id=cluster.id,
            count=count,
            clock_diff_p05=clock_quantiles[0],
            clock_diff_median=clock_quantiles[1],
            clock_diff_p95=clock_quantiles[2],
            path_delay_p05=path_delay_quantiles[0],
            path_delay_median=path_delay_quantiles[1],
            path_delay_p95=path_delay_quantiles[2],
        )
        instance.save()

    @staticmethod
    def invalidate(benchmark: Benchmark, vendor: Vendor, cluster: Cluster):
        BenchmarkSummary.get_query(benchmark, vendor, cluster).delete()

    @staticmethod
    def get_query(benchmark: Benchmark, vendor: Vendor, cluster: Cluster):
        return BenchmarkSummary.objects.filter(
            benchmark_id=benchmark.id,
            vendor_id=vendor.id,
            cluster_id=cluster.id
        )

    def clock_quantiles(self) -> Dict[float, float]:
        return {
            0.05: self.clock_diff_p05,
            0.5: self.clock_diff_median,
            0.95: self.clock_diff_p95,
        }

    class Meta:
        app_label = 'app'
