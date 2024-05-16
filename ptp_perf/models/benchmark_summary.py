from typing import Dict

import pandas as pd
from django.db import models

from ptp_perf.machine import Cluster
from ptp_perf.models import Sample
from ptp_perf.models.endpoint import TimeNormalizationStrategy
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.models.sample_query import SampleQuery
from ptp_perf.profiles.benchmark import Benchmark
from ptp_perf.utilities.django_utilities import DataFormatFloatField, GenericEngineeringFloatField, \
    PercentageFloatField, TimeFormatFloatField, TemperatureFormatFloatField, FrequencyFormatFloatField
from ptp_perf.vendor.vendor import Vendor


class BenchmarkSummary(models.Model):
    id = models.BigAutoField(primary_key=True)
    benchmark_id = models.CharField(max_length=255)
    vendor_id = models.CharField(max_length=255)
    cluster_id = models.CharField(max_length=255)

    count = models.IntegerField()

    # Summary statistics
    clock_diff_median = TimeFormatFloatField(null=True)
    clock_diff_p05 = TimeFormatFloatField(null=True)
    clock_diff_p95 = TimeFormatFloatField(null=True)
    clock_diff_p99 = TimeFormatFloatField(null=True)
    clock_diff_max = TimeFormatFloatField(null=True)
    path_delay_median = TimeFormatFloatField(null=True)
    path_delay_p05 = TimeFormatFloatField(null=True)
    path_delay_p95 = TimeFormatFloatField(null=True)
    path_delay_p99 = TimeFormatFloatField(null=True)
    path_delay_max = TimeFormatFloatField(null=True)
    path_delay_std = TimeFormatFloatField(null=True)

    # Fault statistics
    fault_clock_diff_post_max_max = TimeFormatFloatField(null=True)
    fault_clock_diff_post_max_min = TimeFormatFloatField(null=True)
    fault_ratio_clock_diff_post_max_pre_median_mean = models.FloatField(null=True)

    secondary_fault_clock_diff_post_max_max = TimeFormatFloatField(null=True)
    secondary_fault_clock_diff_post_max_min = TimeFormatFloatField(null=True)
    secondary_fault_ratio_clock_diff_post_max_pre_median_mean = models.FloatField(null=True)

    # Resource consumption data
    proc_cpu_percent = PercentageFloatField(null=True)
    proc_cpu_percent_system = PercentageFloatField(null=True)
    proc_cpu_percent_user = PercentageFloatField(null=True)
    proc_mem_uss = DataFormatFloatField(null=True)
    proc_mem_pss = DataFormatFloatField(null=True)
    proc_mem_rss = DataFormatFloatField(null=True)
    proc_mem_vms = DataFormatFloatField(null=True)
    proc_io_write_count = GenericEngineeringFloatField(null=True)
    proc_io_write_bytes = DataFormatFloatField(null=True)
    proc_io_read_count = GenericEngineeringFloatField(null=True)
    proc_io_read_bytes = DataFormatFloatField(null=True)
    proc_ctx_switches_involuntary = GenericEngineeringFloatField(null=True)
    proc_ctx_switches_voluntary = GenericEngineeringFloatField(null=True)

    sys_sensors_temperature_cpu = TemperatureFormatFloatField(null=True)
    sys_cpu_frequency = FrequencyFormatFloatField(null=True)

    sys_net_ptp_iface_bytes_sent = DataFormatFloatField(null=True)
    sys_net_ptp_iface_packets_sent = GenericEngineeringFloatField(null=True)
    sys_net_ptp_iface_bytes_received = DataFormatFloatField(null=True)
    sys_net_ptp_iface_packets_received = GenericEngineeringFloatField(null=True)

    sys_net_ptp_iface_bytes_total = DataFormatFloatField(null=True)
    sys_net_ptp_iface_packets_total = GenericEngineeringFloatField(null=True)


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
            normalize_time=TimeNormalizationStrategy.NONE, timestamp_merge_append=False
        )

        quantiles = [0.05, 0.5, 0.95, 0.99, 1]

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
            clock_diff_p99=clock_quantiles[3],
            clock_diff_max=clock_quantiles[4],
            path_delay_p05=path_delay_quantiles[0],
            path_delay_median=path_delay_quantiles[1],
            path_delay_p95=path_delay_quantiles[2],
            path_delay_p99=path_delay_quantiles[3],
            path_delay_max=path_delay_quantiles[4],
        )

        # Fault tolerance
        # Per-Endpoint summaries: Primary
        endpoints_primary = data_query.get_endpoint_query().all().values()
        endpoint_frame = pd.DataFrame(endpoints_primary)

        try:
            instance.fault_clock_diff_post_max_max = endpoint_frame['fault_clock_diff_post_max'].max()
            instance.fault_clock_diff_post_max_min = endpoint_frame['fault_clock_diff_post_max'].min()
            instance.fault_ratio_clock_diff_post_max_pre_median_mean = endpoint_frame['fault_ratio_clock_diff_post_max_pre_median'].mean()
        except KeyError:
            pass

        # Per-Endpoint summaries: Secondary
        data_query.endpoint_type = EndpointType.SECONDARY_SLAVE
        endpoints_secondary = data_query.get_endpoint_query().all().values()
        endpoint_frame = pd.DataFrame(endpoints_secondary)

        try:
            instance.secondary_fault_clock_diff_post_max_max = endpoint_frame['fault_clock_diff_post_max'].max()
            instance.secondary_fault_clock_diff_post_max_min = endpoint_frame['fault_clock_diff_post_max'].min()
            instance.secondary_fault_ratio_clock_diff_post_max_pre_median_mean = endpoint_frame['fault_ratio_clock_diff_post_max_pre_median'].mean()
        except KeyError:
            pass

        # Resource consumption data
        for field in instance.__dict__.keys():
            if field.startswith('proc_') or field.startswith('sys_'):
                instance.__dict__[field] = sum(endpoint_dict[field] for endpoint_dict in endpoints_primary if endpoint_dict[field] is not None) / len(endpoints_primary)

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

    def clock_quantiles(self, include_p99_and_max: bool = True) -> Dict[float, float]:
        quantiles = {
            0.05: self.clock_diff_p05,
            0.5: self.clock_diff_median,
            0.95: self.clock_diff_p95,
        }
        if include_p99_and_max:
            quantiles.update({
                0.99: self.clock_diff_p99,
                1.0: self.clock_diff_max,
            })
        return quantiles

    def path_delay_quantiles(self) -> Dict[float, float]:
        return {
            0.05: self.path_delay_p05,
            0.5: self.path_delay_median,
            0.95: self.path_delay_p95,
            0.99: self.path_delay_p99,
            1.0: self.path_delay_max,
        }

    class Meta:
        app_label = 'app'
