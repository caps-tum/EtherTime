import typing

from django.db import models

if typing.TYPE_CHECKING:
    from ptp_perf.profiles.benchmark import Benchmark
    from ptp_perf.vendor.vendor import Vendor


class PTPProfile(models.Model):
    id = models.AutoField(primary_key=True)
    benchmark_id: str = models.CharField(max_length=255, null=False, blank=False)
    vendor_id: str = models.CharField(max_length=255, null=False, blank=False)

    class ProfileState(models.TextChoices):
        RUNNING = "running"
        VALID = "valid"

    state = models.CharField(choices=ProfileState, max_length=255)

    start_time = models.DateTimeField()
    stop_time = models.DateTimeField()


    @property
    def benchmark(self) -> "Benchmark":
        from ptp_perf.registry.benchmark_db import BenchmarkDB
        return BenchmarkDB.get(self.benchmark_id)

    @property
    def vendor(self) -> "Vendor":
        from ptp_perf.vendor.registry import VendorDB
        return VendorDB.get(self.vendor_id)
