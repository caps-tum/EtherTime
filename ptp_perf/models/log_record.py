from django.db import models

from ptp_perf.models.profile import PTPProfile


class LogRecord(models.Model):
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now=True)
    profile = models.ForeignKey(PTPProfile, on_delete=models.CASCADE)

    message = models.TextField(null=False)
