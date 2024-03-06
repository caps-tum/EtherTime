import typing

from django.db import models

if typing.TYPE_CHECKING:
    from ptp_perf.profiles.benchmark import Benchmark
    from ptp_perf.vendor.vendor import Vendor


class PTPProfile(models.Model):
    id = models.AutoField(primary_key=True)
    benchmark_id: str = models.CharField(max_length=255, null=False, blank=False)
    vendor_id: str = models.CharField(max_length=255, null=False, blank=False)

    is_running: bool = models.BooleanField(default=False)
    is_successful: bool = models.BooleanField(default=False)
    is_processed: bool = models.BooleanField(default=False)
    is_corrupted: bool = models.BooleanField(default=False)

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
