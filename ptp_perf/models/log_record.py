from django.db import models

from ptp_perf.models import PTPEndpoint


class LogRecord(models.Model):
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField()
    endpoint = models.ForeignKey(PTPEndpoint, on_delete=models.CASCADE)
    source = models.CharField(max_length=255, null=False, blank=False)

    message = models.TextField(null=False)

    @property
    def machine(self):
        return self.endpoint.machine

    class Meta:
        ordering = ('id',)
        app_label = 'app'

    def __str__(self):
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} {self.endpoint.machine_id} {self.source} {self.message}"
