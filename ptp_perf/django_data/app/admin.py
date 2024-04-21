from io import StringIO
from typing import List
from urllib.parse import urlencode

from admin_actions.admin import ActionsModelAdmin
from django.contrib import admin
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy

from ptp_perf.models import PTPProfile, PTPEndpoint, LogRecord, Sample, Tag, ScheduleTask, BenchmarkSummary
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.test.test_key_metric_variance_charts import KeyMetricVarianceCharts
from ptp_perf.util import unpack_one_value
from ptp_perf.utilities.units import format_time_offset, format_relative


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


def render_timeseries_to_http_response(endpoint: PTPEndpoint):
    chart = endpoint.create_timeseries_chart_convergence()
    chart.tight_layout = True
    return chart_to_http_response(chart)


@admin.register(PTPProfile)
class PTPProfileAdmin(ActionsModelAdmin):
    list_display = ('id', 'benchmark_id', 'vendor_id', 'cluster_id', 'is_running', 'is_successful', 'is_processed',
                    'is_corrupted')
    list_filter = ('benchmark_id', 'vendor_id', 'cluster_id', 'is_running', 'is_successful', 'is_processed',
                   'is_corrupted')
    # inlines = [PTPEndpointInline]
    actions = (delete_analysis_output,)
    actions_row = ('get_endpoints', 'create_timeseries_for_profile',)

    def create_timeseries_for_profile(self, request, pk):
        profile = PTPProfile.objects.get(pk=pk)
        return render_timeseries_to_http_response(profile.endpoint_primary_slave)

    create_timeseries_for_profile.short_description = 'Timeseries'
    create_timeseries_for_profile.url_path = 'profile_timeseries'

    def get_endpoints(self, request, pk):
        profile = PTPProfile.objects.get(pk=pk)
        return HttpResponseRedirect(
            get_endpoint_admin_link(profile.benchmark_id, profile.vendor_id, profile.cluster_id, profile.id)
        )
    get_endpoints.short_description = 'Endpoints'
    get_endpoints.url_path = 'endpoints'


@admin.register(PTPEndpoint)
class PTPEndpointAdmin(ActionsModelAdmin):
    list_display = ('id', 'profile_id', 'benchmark', 'vendor', 'cluster', 'endpoint_type',
                    'clock_diff_median_formatted', 'clock_diff_p95_formatted', 'path_delay_median_formatted',
                    'convergence_duration')
    list_select_related = ('profile',)
    list_filter = ('endpoint_type', 'profile__benchmark_id', 'profile__vendor_id', 'profile__cluster_id')
    actions = (create_key_metric_variance_chart,)
    actions_row = ('create_timeseries',)

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
    clock_diff_median_formatted.short_description = 'Clock Diff Median'

    def clock_diff_p95_formatted(self, endpoint: PTPEndpoint):
        return format_time_offset(endpoint.clock_diff_p95, auto_increase_places=True)

    clock_diff_p95_formatted.admin_order_field = 'clock_diff_p95'
    clock_diff_p95_formatted.short_description = 'Clock Diff 95%'

    def path_delay_median_formatted(self, endpoint: PTPEndpoint):
        return format_time_offset(endpoint.path_delay_median, auto_increase_places=True)

    path_delay_median_formatted.admin_order_field = 'path_delay_median'
    clock_diff_p95_formatted.short_description = 'Path Delay Median'

    def create_timeseries(self, request, pk):
        endpoint: PTPEndpoint = PTPEndpoint.objects.get(pk=pk)
        return render_timeseries_to_http_response(endpoint)

    create_timeseries.short_description = 'Timeseries'
    create_timeseries.url_path = 'timeseries'


@admin.register(LogRecord)
class LogRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'source', 'timestamp', 'message']
    list_filter = ['endpoint__machine_id', 'source', 'endpoint__profile']


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ['id', 'endpoint', "sample_type", "timestamp", 'value']
    list_filter = ['endpoint__profile__benchmark_id', 'endpoint__profile__vendor_id', 'endpoint__machine_id',
                   "sample_type", 'endpoint__profile']


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


def get_endpoint_admin_link(benchmark_id, vendor_id, cluster_id, profile_id: int = None,
                            endpoint_type: EndpointType = None):
    filters = {
        'profile__benchmark_id': benchmark_id,
        'profile__cluster_id': cluster_id,
        'profile__vendor_id': vendor_id,
    }
    if endpoint_type is not None:
        filters['endpoint_type__exact'] = endpoint_type.value
    if profile_id is not None:
        filters['profile__id'] = profile_id

    return reverse_lazy('admin:app_ptpendpoint_changelist') + '?' + urlencode(filters)


@admin.register(BenchmarkSummary)
class BenchmarkSummaryAdmin(ActionsModelAdmin):
    list_display = ('id', 'benchmark_id', 'vendor_id', 'cluster_id', 'count', 'clock_diff_median_formatted',
                    'vs_baseline', 'clock_diff_p95_formatted', 'p95_vs_baseline')
    list_filter = ('benchmark_id', 'vendor_id', 'cluster_id')
    actions_row = ('details',)

    def clock_diff_median_formatted(self, summary: BenchmarkSummary):
        return format_time_offset(summary.clock_diff_median, auto_increase_places=True)

    clock_diff_median_formatted.admin_order_field = 'clock_diff_median'
    clock_diff_median_formatted.short_description = 'Clock Diff Median'

    def clock_diff_p95_formatted(self, summary: BenchmarkSummary):
        return format_time_offset(summary.clock_diff_p95, auto_increase_places=True)

    clock_diff_p95_formatted.admin_order_field = 'clock_diff_p95'
    clock_diff_p95_formatted.short_description = 'Clock Diff 95%'

    def vs_baseline(self, summary: BenchmarkSummary):
        baseline = BenchmarkSummary.objects.get(vendor_id=summary.vendor_id, cluster_id=summary.cluster_id,
                                                benchmark_id=BenchmarkDB.BASE.id)
        return format_relative(summary.clock_diff_median / baseline.clock_diff_median)

    def p95_vs_baseline(self, summary: BenchmarkSummary):
        baseline = BenchmarkSummary.objects.get(vendor_id=summary.vendor_id, cluster_id=summary.cluster_id,
                                                benchmark_id=BenchmarkDB.BASE.id)
        return format_relative(summary.clock_diff_p95 / baseline.clock_diff_p95)

    p95_vs_baseline.short_description = 'Vs Baseline'

    def details(self, request, pk):
        summary = BenchmarkSummary.objects.get(pk=pk)
        return redirect(
            get_endpoint_admin_link(summary.benchmark_id, summary.vendor_id, summary.cluster_id,
                                    endpoint_type=EndpointType.PRIMARY_SLAVE)
        )
    details.short_description = 'Details'
    details.url_path = 'details'
