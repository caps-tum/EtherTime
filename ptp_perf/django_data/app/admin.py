from io import StringIO
from typing import List

from django.contrib import admin
from django.db import transaction
from django.http import HttpResponse

from ptp_perf.models import PTPProfile, PTPEndpoint, LogRecord, Sample, Tag, ScheduleTask, BenchmarkSummary
from ptp_perf.test.test_key_metric_variance_charts import KeyMetricVarianceCharts
from ptp_perf.util import unpack_one_value
from ptp_perf.utilities.units import format_time_offset


class LogRecordInline(admin.TabularInline):
    model = LogRecord

class PTPEndpointInline(admin.TabularInline):
    model = PTPEndpoint


@admin.action(description="Delete analysis output")
def delete_analysis_output(modeladmin, request, queryset):
    profile: PTPProfile
    for profile in queryset.all():
        with transaction.atomic():
            for endpoint in profile.ptpendpoint_set.all():
                endpoint.sample_set.all().delete()
            profile.is_processed = False
            profile.is_corrupted = False
            profile.save()


def chart_to_http_response(chart) -> HttpResponse:
    image_data = StringIO()
    chart.save(image_data, format='svg')
    response = HttpResponse(content_type="image/svg+xml")
    response.write(image_data.getvalue())
    return response


@admin.action(description="Create Key Metric Variance Chart")
def create_key_metric_variance_chart(modeladmin, request, queryset):
    endpoints: List[PTPEndpoint] = list(queryset.all())
    chart = KeyMetricVarianceCharts.create_key_metric_variance_chart(endpoints)
    chart.legend = True
    chart.legend_pos = 'center left'
    chart.legend_kwargs = {
        'bbox_to_anchor': (1, 0.5)
    }
    chart.tight_layout = True
    return chart_to_http_response(chart)


@admin.action(description="View timeseries")
def create_timeseries(modeladmin, request, queryset):
    endpoint: PTPEndpoint = unpack_one_value(queryset.all())
    chart = endpoint.create_timeseries_chart_convergence()
    chart.tight_layout = True
    return chart_to_http_response(chart)



@admin.register(PTPProfile)
class PTPProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'benchmark_id', 'vendor_id', 'cluster_id', 'is_running', 'is_successful', 'is_processed', 'is_corrupted']
    list_filter = ['benchmark_id', 'vendor_id', 'cluster_id', 'is_running', 'is_successful', 'is_processed', 'is_corrupted']
    # inlines = [PTPEndpointInline]
    actions = [delete_analysis_output]

@admin.register(PTPEndpoint)
class PTPEndpointAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile_id', 'benchmark', 'vendor', 'cluster', 'endpoint_type', 'clock_diff_median_formatted', 'clock_diff_p95_formatted', 'path_delay_median_formatted', 'convergence_duration']
    list_select_related = ['profile']
    list_filter = ['endpoint_type', 'profile__benchmark_id', 'profile__vendor_id', 'profile__cluster_id']
    actions = [create_key_metric_variance_chart, create_timeseries]

    def benchmark(self, endpoint: PTPEndpoint):
        return endpoint.profile.benchmark.name

    def vendor(self, endpoint: PTPEndpoint):
        return endpoint.profile.vendor.name

    def cluster(self, endpoint: PTPEndpoint):
        return endpoint.profile.cluster

    def profile_id(self, endpoint: PTPEndpoint):
        return endpoint.profile.id
    # inlines = [LogRecordInline]

    def clock_diff_median_formatted(self, endpoint: PTPEndpoint):
        return format_time_offset(endpoint.clock_diff_median, auto_increase_places=True)
    clock_diff_median_formatted.admin_order_field = 'clock_diff_median'

    def clock_diff_p95_formatted(self, endpoint: PTPEndpoint):
        return format_time_offset(endpoint.clock_diff_p95, auto_increase_places=True)
    clock_diff_p95_formatted.admin_order_field = 'clock_diff_p95'

    def path_delay_median_formatted(self, endpoint: PTPEndpoint):
        return format_time_offset(endpoint.path_delay_median, auto_increase_places=True)
    path_delay_median_formatted.admin_order_field = 'path_delay_median'

@admin.register(LogRecord)
class LogRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'source', 'timestamp', 'message']
    list_filter = ['endpoint__profile', 'endpoint__machine_id', 'source']

@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ['id', 'endpoint', "sample_type", "timestamp", 'value']
    list_filter = ['endpoint__profile__benchmark_id', 'endpoint__profile__vendor_id', 'endpoint__machine_id', "sample_type"]

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    pass

@admin.action(description="Toggle paused")
def toggle_pause(modeladmin, request, queryset):
    task: ScheduleTask
    with transaction.atomic():
        for task in queryset.all():
            task.paused = not task.paused
            task.save()


@admin.register(ScheduleTask)
class ScheduleTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'paused', 'estimated_time', 'success', 'start_time', 'completion_time']
    list_filter = ['success', 'paused']
    actions = [toggle_pause]


@admin.register(BenchmarkSummary)
class BenchmarkSummaryAdmin(admin.ModelAdmin):
    list_display = ['id', 'benchmark_id', 'vendor_id', 'cluster_id', 'count', 'clock_diff_median_formatted', 'clock_diff_p95_formatted']
    list_filter = ['benchmark_id', 'vendor_id', 'cluster_id']

    def clock_diff_median_formatted(self, summary: BenchmarkSummary):
        return format_time_offset(summary.clock_diff_median, auto_increase_places=True)
    clock_diff_median_formatted.admin_order_field = 'clock_diff_median'

    def clock_diff_p95_formatted(self, summary: BenchmarkSummary):
        return format_time_offset(summary.clock_diff_median, auto_increase_places=True)
    clock_diff_p95_formatted.admin_order_field = 'clock_diff_p95'
