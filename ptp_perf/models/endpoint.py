from django.db import models
from django.db.models import CASCADE

from ptp_perf.models.profile import PTPProfile


class PTPEndpoint(models.Model):
    id = models.AutoField(primary_key=True)

    profile = models.ForeignKey(PTPProfile, on_delete=CASCADE)
    machine_id = models.CharField(max_length=255)

    # Summary statistics
    clock_diff_median = models.FloatField(null=True, editable=False)
    clock_diff_p99 = models.FloatField(null=True, editable=False)
    path_delay_median = models.FloatField(null=True, editable=False)

    # Convergence statistics
    convergence_time = models.DateTimeField(null=True, editable=False)
    convergence_max_offset = models.FloatField(null=True, editable=False)
    convergence_rate = models.FloatField(null=True, editable=False)

