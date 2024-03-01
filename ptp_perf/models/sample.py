from django.db import models

from ptp_perf.models.endpoint import PTPEndpoint

class Sample(models.Model):
    id = models.AutoField(primary_key=True)
    endpoint = models.ForeignKey(PTPEndpoint, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(null=False)

    class SampleType(models.TextChoices):
        CLOCK_DIFF = "CLOCK_DIFF"
        PATH_DELAY = "PATH_DELAY"
        FAULT = "FAULT"

    sample_type = models.CharField(choices=SampleType, null=False, max_length=255)
