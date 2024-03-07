from django.contrib import admin

from ptp_perf.models import PTPProfile, PTPEndpoint, LogRecord, Sample, Tag


# Register your models here.

@admin.register(PTPProfile)
class PTPProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'benchmark_id', 'vendor_id', 'is_running', 'is_successful', 'is_processed', 'is_corrupted']

@admin.register(PTPEndpoint)
class PTPEndpointAdmin(admin.ModelAdmin):
    pass

@admin.register(LogRecord)
class LogRecordAdmin(admin.ModelAdmin):
    pass

@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    pass

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    pass
