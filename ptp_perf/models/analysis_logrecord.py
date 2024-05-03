from django.db import models

from ptp_perf.models import PTPProfile
from ptp_perf.models.loglevel import LogLevel


class AnalysisLogRecord(models.Model):
    id = models.AutoField(primary_key=True)
    profile = models.ForeignKey(PTPProfile, on_delete=models.CASCADE, help_text='The profile being analyzed.')
    level = models.IntegerField(choices=LogLevel, help_text='The level of importance of the message.')
    timestamp = models.DateField()
    message = models.TextField(null=True)

    class Meta:
        app_label = 'app'
