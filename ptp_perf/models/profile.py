import typing

from django.db import models

from ptp_perf.models.endpoint_type import EndpointType

if typing.TYPE_CHECKING:
    from ptp_perf.profiles.benchmark import Benchmark
    from ptp_perf.vendor.vendor import Vendor
    from ptp_perf.models import PTPEndpoint


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
    def endpoint_master(self) -> "PTPEndpoint":
        return self.ptpendpoint_set.filter(endpoint_type=EndpointType.MASTER).get()

    @property
    def endpoint_primary_slave(self) -> "PTPEndpoint":
        return self.ptpendpoint_set.filter(endpoint_type=EndpointType.PRIMARY_SLAVE).get()

    @property
    def endpoint_secondary_slave(self) -> "PTPEndpoint":
        return self.ptpendpoint_set.filter(endpoint_type=EndpointType.SECONDARY_SLAVE).get()

    @property
    def vendor(self) -> "Vendor":
        from ptp_perf.vendor.registry import VendorDB
        return VendorDB.get(self.vendor_id)

    def __str__(self):
        return f"{self.benchmark} (#{self.id}, {self.vendor}, {self.start_time})"


    class Meta:
        app_label = 'app'
        db_table = "ptp_perf_ptpprofile"
