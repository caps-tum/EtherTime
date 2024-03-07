from django.db import models

from ptp_perf.models import PTPEndpoint


class LogRecord(models.Model):
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField()
    endpoint = models.ForeignKey(PTPEndpoint, on_delete=models.CASCADE)
    source = models.CharField(max_length=255, null=False, blank=False)

    message = models.TextField(null=False)


    class Meta:
        ordering = ('id',)
        app_label = 'app'
        db_table = "ptp_perf_logrecord"
