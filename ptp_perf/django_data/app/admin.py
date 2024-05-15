from io import StringIO
from typing import List, Callable, Any
from urllib.parse import urlencode

from admin_actions.admin import ActionsModelAdmin
from django.contrib import admin, messages
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy

from ptp_perf.charts.interactive_timeseries_chart import InteractiveTimeseriesChart
from ptp_perf.django_data.app.management.commands.analyze import run_analysis
from ptp_perf.models import PTPProfile, PTPEndpoint, LogRecord, Sample, Tag, ScheduleTask, BenchmarkSummary
from ptp_perf.models.analysis_logrecord import AnalysisLogRecord
from ptp_perf.models.endpoint import TimeNormalizationStrategy
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.test.test_key_metric_variance_charts import KeyMetricVarianceCharts
from ptp_perf.utilities.django_utilities import CustomFormatsAdmin
from ptp_perf.utilities.units import format_time_offset, format_relative


class LogRecordInline(admin.TabularInline):
    model = LogRecord


class PTPEndpointInline(admin.TabularInline):
    model = PTPEndpoint


@admin.action(description="Delete analysis output")
def delete_analysis_output(modeladmin, request, queryset):
    profile: PTPProfile
    with transaction.atomic():
        for profile in queryset.all():
            profile.clear_analysis_data()

@admin.action(description="Reanalyze profile")
def reanalyze_profile(modeladmin, request, queryset):
    profile: PTPProfile
    for profile in queryset.all():
        profile.clear_analysis_data()
    run_analysis(force=False)
    for profile in queryset.all():
        messages.info(request, f"Analyzed profile {profile}:",)
        for record in profile.analysislogrecord_set.all():
            messages.add_message(request, record.level, record.message)

def chart_to_svg_string(chart) -> str:
    image_data = StringIO()
    chart.save(image_data, format='svg')
    return image_data.getvalue()

def chart_to_http_response(chart) -> HttpResponse:
    response = HttpResponse(content_type="image/svg+xml")
    response.write(chart_to_svg_string(chart))
    return response


@admin.action(description="Create Key Metric Variance Chart")
def create_key_metric_variance_chart(modeladmin, request, queryset):
    endpoints: List[PTPEndpoint] = list(queryset.all())
    chart = KeyMetricVarianceCharts.create_key_metric_variance_chart(endpoints)
    chart.ylimit_top_use_always = False
    chart.ylimit_top = None
    chart.legend = True
    chart.legend_pos = 'center left'
    chart.legend_kwargs = {
        'bbox_to_anchor': (1, 0.5)
    }
    chart.tight_layout = True
    return chart_to_http_response(chart)


def render_timeseries_to_http_response(*endpoints: PTPEndpoint):
    charts_as_svg = ""
    for endpoint in endpoints:
        chart = endpoint.create_timeseries_chart_convergence(normalization=TimeNormalizationStrategy.PROFILE_START)
        chart.tight_layout = True
        charts_as_svg += f"""
            <h3>{endpoint.endpoint_type}</h3>
            <p>{endpoint} (<a href="/admin/app/ptpendpoint/interactive/{endpoint.id}/">Interactive Chart</a>)</p>
            {chart_to_svg_string(chart)}
            <br>
        """

    response = HttpResponse()
    response.write(
        f"""
<!DOCTYPE html>
<html>
<body>

{charts_as_svg}

</body>
</html> 
"""
    )
    return response

def render_timeseries_interactive_chart(endpoint: PTPEndpoint):
    document = InteractiveTimeseriesChart().render_to_html(endpoint)
    return HttpResponse(content=document)

@admin.register(PTPProfile)
class PTPProfileAdmin(ActionsModelAdmin):
    list_display = ('id', 'benchmark_id', 'vendor_id', 'cluster_id', 'is_running', 'is_successful', 'is_processed',
                    'is_corrupted', 'duration')
    list_filter = ('benchmark_id', 'vendor_id', 'cluster_id', 'is_running', 'is_successful', 'is_processed',
                   'is_corrupted')
    # inlines = [PTPEndpointInline]
    actions = (delete_analysis_output, reanalyze_profile)
    actions_row = ('get_endpoints', 'create_timeseries_for_profile', 'redirect_logrecord', 'profile_redirect_analysislogrecord')

    def create_timeseries_for_profile(self, request, pk):
        profile = PTPProfile.objects.get(pk=pk)
        return render_timeseries_to_http_response(*profile.ptpendpoint_set.all())

    create_timeseries_for_profile.short_description = 'Timeseries'
    create_timeseries_for_profile.url_path = 'profile_timeseries'

    def get_endpoints(self, request, pk):
        profile = PTPProfile.objects.get(pk=pk)
        return HttpResponseRedirect(
            get_endpoint_admin_link(profile.benchmark_id, profile.vendor_id, profile.cluster_id, profile.id)
        )

    get_endpoints.short_description = 'Endpoints'
    get_endpoints.url_path = 'endpoints'

    def redirect_logrecord(self, request, pk):
        return HttpResponseRedirect(
            get_admin_redirect_link(LogRecord, {'endpoint__profile__id__exact': pk})
        )
    redirect_logrecord.short_description = 'Log'
    redirect_logrecord.url_path = 'logrecord'

    def profile_redirect_analysislogrecord(self, request, pk):
        return HttpResponseRedirect(
            get_admin_redirect_link(AnalysisLogRecord, {'profile_id': pk})
        )
    profile_redirect_analysislogrecord.short_description = 'Analysis Log'
    profile_redirect_analysislogrecord.url_path = 'analysislogrecord'


@admin.register(PTPEndpoint)
class PTPEndpointAdmin(CustomFormatsAdmin):
    list_display = ('id', 'profile_id', 'benchmark', 'vendor', 'cluster', 'machine', 'endpoint_type',
                    'clock_diff_median_formatted', 'clock_diff_p95_formatted', 'path_delay_median_formatted',
                    'missing_samples_percent',
                    'convergence_duration')
    list_select_related = ('profile',)
    list_filter = ('endpoint_type', 'profile__benchmark_id', 'profile__vendor_id', 'profile__cluster_id')
    actions = (create_key_metric_variance_chart,)
    actions_row = ('create_timeseries', 'create_interactive_timeseries', 'endpoint_redirect_logrecord')

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

    def create_interactive_timeseries(self, request, pk):
        endpoint: PTPEndpoint = PTPEndpoint.objects.get(pk=pk)
        return render_timeseries_interactive_chart(endpoint)

    create_interactive_timeseries.short_description = 'Interactive'
    create_interactive_timeseries.url_path = 'interactive'

    def endpoint_redirect_logrecord(self, request, pk):
        return HttpResponseRedirect(
            get_admin_redirect_link(LogRecord, {'endpoint_id__exact': pk})
        )
    endpoint_redirect_logrecord.short_description = 'Log'
    endpoint_redirect_logrecord.url_path = 'logrecord'


def format_time_offset_for_admin(value: float) -> str:
    return format_time_offset(value, auto_increase_places=True)


def formatted_field(field: Callable[[Any], float], short_description: str, order_field: str,
                    format_function: Callable = format_time_offset_for_admin):
    def inner_function(self, value):
        return format_function(field(value))

    inner_function.short_description = short_description
    inner_function.admin_order_field = order_field
    return inner_function


def create_modeladmin(modeladmin, model, name=None):
    # Stack-overflow https://stackoverflow.com/questions/2223375/multiple-modeladmins-views-for-same-model-in-django-admin
    class Meta:
        proxy = True
        app_label = model._meta.app_label

    attrs = {'__module__': '', 'Meta': Meta}

    newmodel = type(name, (model,), attrs)

    admin.site.register(newmodel, modeladmin)
    return modeladmin


class PTPEndpointFaultAdmin(PTPEndpointAdmin):
    list_display = ('id', 'profile_id', 'benchmark', 'vendor', 'cluster', 'endpoint_type',
                    'clock_diff_pre_median_formatted', 'clock_diff_post_max_formatted',
                    'fault_ratio_clock_diff_median_formatted', 'fault_actual_duration')

    def get_queryset(self, request):
        return super().get_queryset(request).filter(fault_actual_duration__isnull=False)

    clock_diff_pre_median_formatted = formatted_field(
        lambda endpoint: endpoint.fault_clock_diff_pre_median,
        "Pre Clock Diff Median", "fault_clock_diff_pre_median",
    )

    clock_diff_post_max_formatted = formatted_field(
        lambda endpoint: endpoint.fault_clock_diff_post_max,
        "Post Clock Diff Max", "fault_clock_diff_post_max",
    )

    fault_ratio_clock_diff_median_formatted = formatted_field(
        lambda endpoint: endpoint.fault_ratio_clock_diff_post_max_pre_median,
        "Max/Median Ratio", "fault_ratio_clock_diff_post_max_pre_median",
        format_function=format_relative,
    )


create_modeladmin(PTPEndpointFaultAdmin, PTPEndpoint, "endpoint-fault")


@admin.register(LogRecord)
class LogRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'machine', 'source', 'timestamp', 'message']
    list_filter = ['endpoint__machine_id', 'source', 'endpoint__profile']
    list_per_page = 1000

@admin.register(AnalysisLogRecord)
class LogRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'level', 'timestamp', 'message']
    list_filter = ['profile', 'level']


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ['id', 'endpoint', "sample_type", "timestamp", 'value']
    list_filter = ['endpoint__profile__benchmark_id', 'endpoint__profile__vendor_id', 'endpoint__machine_id',
                   "sample_type", 'endpoint__profile']
    list_per_page = 1000


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    pass




@admin.register(ScheduleTask)
class ScheduleTaskAdmin(ActionsModelAdmin):
    list_display = ('id', 'priority', 'name', 'paused', 'estimated_time', 'success', 'start_time', 'completion_time')
    list_filter = ('success', 'paused')
    actions = ('toggle_pause', 'update_priority')
    actions_list = ('toggle_pause', 'update_priority')
    actions_row = ('update_priority_single',)

    @admin.action(description="Toggle paused")
    def toggle_pause(self, request, queryset):
        task: ScheduleTask
        with transaction.atomic():
            for task in queryset.all():
                task.paused = not task.paused
                task.save()

    @admin.action(description="Prioritize")
    def update_priority(self, request, queryset: QuerySet):
        with transaction.atomic():
            for task in queryset.all():
                task.priority += 1
                task.save()
        messages.info(request, f"Updated priorities of {queryset.count()} tasks.")


    def update_priority_single(self, request, pk):
        task = ScheduleTask.objects.get(pk=pk)
        task.priority += 1
        task.save()
        messages.info(request, f"Prioritized task {task} to priority {task.priority}")
        return redirect(get_admin_redirect_link(ScheduleTask, filters={}))
    update_priority_single.short_description = 'Prioritize Task'
    update_priority_single.url_path = 'prioritize'




def get_admin_redirect_link(model, filters: dict):
    return reverse_lazy(f'admin:app_{model._meta.model_name}_changelist') + '?' + urlencode(filters)

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
        filters['profile_id'] = profile_id

    return get_admin_redirect_link(PTPEndpoint, filters)

def get_profile_admin_link(benchmark_id, vendor_id, cluster_id):
    filters = {
        'benchmark_id': benchmark_id,
        'cluster_id': cluster_id,
        'vendor_id': vendor_id,
    }
    return get_admin_redirect_link(PTPProfile, filters)


@admin.register(BenchmarkSummary)
class BenchmarkSummaryAdmin(CustomFormatsAdmin):
    list_display = ('id', 'benchmark_id', 'vendor_id', 'cluster_id', 'count', 'clock_diff_median',
                    'vs_baseline', 'clock_diff_p95', 'p95_vs_baseline')
    list_filter = ('benchmark_id', 'vendor_id', 'cluster_id')
    actions_row = ('summary_create_timeseries', 'endpoints', 'profiles')

    def vs_baseline(self, summary: BenchmarkSummary):
        baseline = BenchmarkSummary.objects.get(vendor_id=summary.vendor_id, cluster_id=summary.cluster_id,
                                                benchmark_id=BenchmarkDB.BASE.id)
        return format_relative(summary.clock_diff_median / baseline.clock_diff_median)

    def p95_vs_baseline(self, summary: BenchmarkSummary):
        baseline = BenchmarkSummary.objects.get(vendor_id=summary.vendor_id, cluster_id=summary.cluster_id,
                                                benchmark_id=BenchmarkDB.BASE.id)
        return format_relative(summary.clock_diff_p95 / baseline.clock_diff_p95)

    p95_vs_baseline.short_description = 'Vs Baseline'

    def endpoints(self, request, pk):
        summary = BenchmarkSummary.objects.get(pk=pk)
        return redirect(
            get_endpoint_admin_link(summary.benchmark_id, summary.vendor_id, summary.cluster_id,
                                    endpoint_type=EndpointType.PRIMARY_SLAVE)
        )
    endpoints.short_description = 'Endpoints'
    endpoints.url_path = 'endpoints'

    def profiles(self, request, pk):
        summary = BenchmarkSummary.objects.get(pk=pk)
        return redirect(
            get_profile_admin_link(summary.benchmark_id, summary.vendor_id, summary.cluster_id)
        )
    profiles.short_description = 'Profiles'
    profiles.url_path = 'Profiles'

    def summary_create_timeseries(self, request, pk):
        summary = BenchmarkSummary.objects.get(pk=pk)
        endpoints = PTPEndpoint.objects.filter(
            profile__benchmark_id=summary.benchmark_id,
            profile__vendor_id=summary.vendor_id,
            profile__cluster_id=summary.cluster_id,
            endpoint_type__in=[EndpointType.PRIMARY_SLAVE, EndpointType.SECONDARY_SLAVE],
        )
        return render_timeseries_to_http_response(*endpoints.all())
    summary_create_timeseries.short_description = 'Timeseries'
    summary_create_timeseries.url_path = 'summary_timeseries'

class ResourceConsumptionEndpointAdmin(PTPEndpointAdmin):
    list_display = (
        'id', 'benchmark', 'vendor', 'cluster', 'endpoint_type',
        'clock_diff_median',
        'proc_cpu_percent', 'proc_cpu_percent_system', 'proc_cpu_percent_user',
        'sys_cpu_frequency', 'sys_sensors_temperature_cpu',
        'proc_mem_uss', 'proc_mem_pss',  'proc_mem_rss', 'proc_mem_vms',
        'sys_net_ptp_iface_packets_total', 'sys_net_ptp_iface_bytes_total',
        'sys_net_ptp_iface_packets_sent', 'sys_net_ptp_iface_bytes_sent',
        'sys_net_ptp_iface_packets_received', 'sys_net_ptp_iface_bytes_received',
        'proc_ctx_switches_voluntary', 'proc_ctx_switches_involuntary',
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(proc_cpu_percent__isnull=False)

create_modeladmin(ResourceConsumptionEndpointAdmin, PTPEndpoint, "endpoint-resource-consumption")

class ResourceConsumptionSummaryAdmin(CustomFormatsAdmin):
    list_display = (
        'id', 'benchmark_id', 'vendor_id', 'cluster_id', 'count',
        'clock_diff_median',
        'proc_cpu_percent', 'proc_cpu_percent_system', 'proc_cpu_percent_user',
        'sys_cpu_frequency', 'sys_sensors_temperature_cpu',
        'proc_mem_uss', 'proc_mem_pss',  'proc_mem_rss', 'proc_mem_vms',
        'sys_net_ptp_iface_packets_total', 'sys_net_ptp_iface_bytes_total',
        'sys_net_ptp_iface_packets_sent', 'sys_net_ptp_iface_bytes_sent',
        'sys_net_ptp_iface_packets_received', 'sys_net_ptp_iface_bytes_received',
        'proc_ctx_switches_voluntary', 'proc_ctx_switches_involuntary',
    )
    list_filter = ('benchmark_id', 'vendor_id', 'cluster_id')

    def get_queryset(self, request):
        return super().get_queryset(request).filter(proc_cpu_percent__isnull=False)


create_modeladmin(ResourceConsumptionSummaryAdmin, BenchmarkSummary, "summary-resource-consumption")
