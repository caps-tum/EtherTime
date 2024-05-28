from django.db import models

from ptp_perf.models.endpoint import PTPEndpoint

class Sample(models.Model):
    """
    A sample of a performance metric taken from a PTP endpoint, parsed into timeseries data.
    Types of samples include:
    - CLOCK_DIFF: The difference between the local and remote clock.
    - PATH_DELAY: The time it takes for a message to travel between the local and remote endpoint.
    - FAULT: A fault detected by the endpoint.
    """
    id = models.AutoField(primary_key=True)
    endpoint = models.ForeignKey(PTPEndpoint, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(null=False)

    class SampleType(models.TextChoices):
        CLOCK_DIFF = "CLOCK_DIFF"
        PATH_DELAY = "PATH_DELAY"
        FAULT = "FAULT"

    sample_type = models.CharField(choices=SampleType, null=False, max_length=255)

    value = models.BigIntegerField(null=False)

    def __str__(self):
        return f"{self.timestamp}: {self.sample_type}={self.value}"

    class Meta:
        app_label = 'app'
        ordering = ['id']
