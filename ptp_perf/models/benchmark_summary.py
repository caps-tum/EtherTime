import dataclasses
from typing import Dict

import pandas as pd
from django.db import models

from ptp_perf.machine import Cluster
from ptp_perf.models import Sample, PTPEndpoint
from ptp_perf.models.endpoint import TimeNormalizationStrategy
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.models.exceptions import NoDataError
from ptp_perf.models.sample_query import SampleQuery
from ptp_perf.profiles.benchmark import Benchmark
from ptp_perf.utilities.django_utilities import DataFormatFloatField, GenericEngineeringFloatField, \
    PercentageFloatField, TimeFormatFloatField, TemperatureFormatFloatField, FrequencyFormatFloatField
from ptp_perf.utilities.pandas_utilities import frame_column
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
    clock_diff_mean = TimeFormatFloatField(null=True)
    path_delay_median = TimeFormatFloatField(null=True)
    path_delay_p05 = TimeFormatFloatField(null=True)
    path_delay_p95 = TimeFormatFloatField(null=True)
    path_delay_p99 = TimeFormatFloatField(null=True)
    path_delay_max = TimeFormatFloatField(null=True)
    path_delay_std = TimeFormatFloatField(null=True)

    # Convergence
    convergence_duration = models.DurationField(null=True)
    convergence_max_offset = TimeFormatFloatField(null=True)
    convergence_rate = TimeFormatFloatField(null=True)

    converged_percentage = PercentageFloatField(null=True)
    converged_samples = models.IntegerField(null=True)

    missing_samples_primary_percent = PercentageFloatField(null=True)
    missing_samples_all_percent = PercentageFloatField(null=True)


    # Fault statistics
    fault_clock_diff_mid_max_max = TimeFormatFloatField(null=True)


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

        instance = BenchmarkSummary(
            benchmark_id=benchmark.id,
            vendor_id=vendor.id,
            cluster_id=cluster.id,
        )

        data_query = SampleQuery(
            benchmark=benchmark,
            vendor=vendor,
            cluster=cluster,
            endpoint_type=EndpointType.PRIMARY_SLAVE,
            normalize_time=TimeNormalizationStrategy.NONE, timestamp_merge_append=False
        )

        quantiles = [0.05, 0.5, 0.95, 0.99, 1]

        try:
            clock_data = data_query.run(Sample.SampleType.CLOCK_DIFF)
            instance.count = len(clock_data.index.get_level_values("endpoint_id").unique())

            clock_data = clock_data.droplevel('endpoint_id').abs()
            clock_quantiles = clock_data.quantile(quantiles).values

            instance.clock_diff_p05 = clock_quantiles[0]
            instance.clock_diff_median = clock_quantiles[1]
            instance.clock_diff_p95 = clock_quantiles[2]
            instance.clock_diff_p99 = clock_quantiles[3]
            instance.clock_diff_max = clock_quantiles[4]
            instance.clock_diff_mean = clock_data.mean()

        except NoDataError:
            instance.count = 0

        try:
            path_delay_data = data_query.run(Sample.SampleType.PATH_DELAY)
            path_delay_data = path_delay_data.droplevel('endpoint_id')
            path_delay_quantiles = path_delay_data.quantile(quantiles).values

            instance.path_delay_p05=path_delay_quantiles[0]
            instance.path_delay_median=path_delay_quantiles[1]
            instance.path_delay_p95=path_delay_quantiles[2]
            instance.path_delay_p99=path_delay_quantiles[3]
            instance.path_delay_max=path_delay_quantiles[4]

        except NoDataError:
            pass

        print(f'{benchmark} {vendor} {cluster}: {instance.count} endpoints summarized')

        # Fault tolerance
        # Per-Endpoint summaries: Primary
        endpoints_primary_queryset = data_query.get_endpoint_query().all().values()
        endpoints_primary = pd.DataFrame(endpoints_primary_queryset)
        endpoints_all_slaves = pd.DataFrame(
            dataclasses.replace(data_query, endpoint_type=None).get_endpoint_query().filter(
                endpoint_type__in=[EndpointType.PRIMARY_SLAVE, EndpointType.SECONDARY_SLAVE, EndpointType.TERTIARY_SLAVE],
            ).all().values()
        )

        # Convergence
        try:
            instance.convergence_duration = endpoints_primary[frame_column(PTPEndpoint.convergence_duration)].mean()
            instance.convergence_max_offset = endpoints_primary[frame_column(PTPEndpoint.convergence_max_offset)].mean()
            instance.convergence_rate = endpoints_primary[frame_column(PTPEndpoint.convergence_rate)].mean()

            instance.converged_percentage = endpoints_primary[frame_column(PTPEndpoint.converged_percentage)].mean()
            instance.converged_samples = endpoints_primary[frame_column(PTPEndpoint.converged_samples)].mean()
        except KeyError:
            pass

        # Missing samples
        try:
            instance.missing_samples_primary_percent = endpoints_primary[frame_column(PTPEndpoint.missing_samples_percent)].mean()
            instance.missing_samples_all_percent = endpoints_all_slaves[frame_column(PTPEndpoint.missing_samples_percent)].mean()
        except KeyError:
            pass

        try:
            instance.fault_clock_diff_post_max_max = endpoints_primary[frame_column(PTPEndpoint.fault_clock_diff_mid_max)].max()
        except KeyError:
            pass

        try:
            instance.fault_clock_diff_post_max_max = endpoints_primary['fault_clock_diff_post_max'].max()
            instance.fault_clock_diff_post_max_min = endpoints_primary['fault_clock_diff_post_max'].min()
            instance.fault_ratio_clock_diff_post_max_pre_median_mean = endpoints_primary['fault_ratio_clock_diff_post_max_pre_median'].mean()
        except KeyError:
            pass

        # Per-Endpoint summaries: Secondary
        data_query.endpoint_type = EndpointType.SECONDARY_SLAVE
        endpoints_secondary = pd.DataFrame(data_query.get_endpoint_query().all().values())

        try:
            instance.secondary_fault_clock_diff_post_max_max = endpoints_secondary['fault_clock_diff_post_max'].max()
            instance.secondary_fault_clock_diff_post_max_min = endpoints_secondary['fault_clock_diff_post_max'].min()
            instance.secondary_fault_ratio_clock_diff_post_max_pre_median_mean = endpoints_secondary['fault_ratio_clock_diff_post_max_pre_median'].mean()
        except KeyError:
            pass

        # Resource consumption data
        # Looks like it comes just from the primary slave
        num_primary_endpoints = len(endpoints_primary_queryset)
        if num_primary_endpoints > 0:
            for field in instance.__dict__.keys():
                if field.startswith('proc_') or field.startswith('sys_'):
                    instance.__dict__[field] = sum(endpoint_dict[field] for endpoint_dict in endpoints_primary_queryset if endpoint_dict[field] is not None) / num_primary_endpoints

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
