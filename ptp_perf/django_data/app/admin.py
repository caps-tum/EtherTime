from django.contrib import admin
from django.db import transaction

from ptp_perf.models import PTPProfile, PTPEndpoint, LogRecord, Sample, Tag, ScheduleTask



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


@admin.register(PTPProfile)
class PTPProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'benchmark_id', 'vendor_id', 'cluster_id', 'is_running', 'is_successful', 'is_processed', 'is_corrupted']
    list_filter = ['benchmark_id', 'vendor_id', 'cluster_id', 'is_running', 'is_successful', 'is_processed', 'is_corrupted']
    # inlines = [PTPEndpointInline]
    actions = [delete_analysis_output]

@admin.register(PTPEndpoint)
class PTPEndpointAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile_id', 'vendor', 'cluster', 'endpoint_type', 'clock_diff_median', 'clock_diff_p95', 'path_delay_median']
    list_select_related = ['profile']
    list_filter = ['endpoint_type', 'profile__vendor_id', 'profile__cluster_id', 'profile_id']

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
    list_display = ['id', 'endpoint', "sample_type", 'value']
    list_filter = ['endpoint__profile', 'endpoint__machine_id', "sample_type"]

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    pass

@admin.register(ScheduleTask)
class ScheduleTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'estimated_time', 'success', 'start_time', 'completion_time']
