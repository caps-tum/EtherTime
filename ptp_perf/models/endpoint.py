import logging
from datetime import datetime

from django.db import models
from django.db.models import CASCADE

from ptp_perf import config
from ptp_perf.machine import Machine
from ptp_perf.models.profile import PTPProfile
from ptp_perf.profiles.benchmark import Benchmark


class PTPEndpoint(models.Model):
    id = models.AutoField(primary_key=True)

    profile: PTPProfile = models.ForeignKey(PTPProfile, on_delete=CASCADE)
    machine_id = models.CharField(max_length=255)

    # Summary statistics
    clock_diff_median = models.FloatField(null=True, editable=False)
    clock_diff_p99 = models.FloatField(null=True, editable=False)
    path_delay_median = models.FloatField(null=True, editable=False)

    # Convergence statistics
    convergence_time = models.DateTimeField(null=True, editable=False)
    convergence_max_offset = models.FloatField(null=True, editable=False)
    convergence_rate = models.FloatField(null=True, editable=False)


    def log(self, message: str, source: str):
        """Log to a logger with the name 'source'. Message will be intercepted by the log to database adapter and
        saved as a log record."""
        logging.getLogger(source).info(message)

    @property
    def benchmark(self) -> Benchmark:
        from ptp_perf.registry.benchmark_db import BenchmarkDB
        return BenchmarkDB.get(self.profile.benchmark_id)

    @property
    def machine(self) -> Machine:
        return config.machines.get(self.machine_id)
