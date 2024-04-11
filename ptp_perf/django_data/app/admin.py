from io import StringIO
from typing import List

from django.contrib import admin
from django.core import serializers
from django.db import transaction
from django.http import HttpResponse

from ptp_perf.models import PTPProfile, PTPEndpoint, LogRecord, Sample, Tag, ScheduleTask
from ptp_perf.test.test_key_metric_variance_charts import KeyMetricVarianceCharts


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

    image_data = StringIO()
    chart.save(image_data, format='svg')
    response = HttpResponse(content_type="image/svg+xml")
    response.write(image_data.getvalue())
    # serializers.serialize("json", queryset, stream=response)
    return response
    # return HttpResponse(
    #     image_data,
    #     # content_type="image/svg",
    # )


@admin.register(PTPProfile)
class PTPProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'benchmark_id', 'vendor_id', 'cluster_id', 'is_running', 'is_successful', 'is_processed', 'is_corrupted']
    list_filter = ['benchmark_id', 'vendor_id', 'cluster_id', 'is_running', 'is_successful', 'is_processed', 'is_corrupted']
    # inlines = [PTPEndpointInline]
    actions = [delete_analysis_output]

@admin.register(PTPEndpoint)
class PTPEndpointAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile_id', 'benchmark', 'vendor', 'cluster', 'endpoint_type', 'clock_diff_median', 'clock_diff_p95', 'path_delay_median']
    list_select_related = ['profile']
    list_filter = ['endpoint_type', 'profile__benchmark_id', 'profile__vendor_id', 'profile__cluster_id']
    actions = [create_key_metric_variance_chart]

    def benchmark(self, endpoint: PTPEndpoint):
        return endpoint.profile.benchmark.name

    def vendor(self, endpoint: PTPEndpoint):
        return endpoint.profile.vendor.name

    def cluster(self, endpoint: PTPEndpoint):
        return endpoint.profile.cluster

    def profile_id(self, endpoint: PTPEndpoint):
        return endpoint.profile.id
    # inlines = [LogRecordInline]

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

@admin.register(ScheduleTask)
class ScheduleTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'estimated_time', 'success', 'start_time', 'completion_time']
