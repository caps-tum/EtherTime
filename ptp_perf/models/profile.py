import dataclasses
import json
import logging
import typing
from datetime import timedelta

from django.db import models
from django.forms import model_to_dict

from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.models.loglevel import LogLevel
from ptp_perf.util import str_join
from ptp_perf.utilities.django_utilities import get_server_datetime
from ptp_perf.utilities.serialization import ModelJSONEncoder

if typing.TYPE_CHECKING:
    from ptp_perf.machine import Cluster
    from ptp_perf.profiles.benchmark import Benchmark
    from ptp_perf.vendor.vendor import Vendor
    from ptp_perf.models import PTPEndpoint


class PTPProfile(models.Model):
    id = models.AutoField(primary_key=True)
    benchmark_id: str = models.CharField(max_length=255, null=False, blank=False)
    vendor_id: str = models.CharField(max_length=255, null=False, blank=False)
    cluster_id: str = models.CharField(max_length=255, null=False, blank=False)

    is_running: bool = models.BooleanField(default=False)
    is_successful: bool = models.BooleanField(default=False)
    is_processed: bool = models.BooleanField(default=False)
    is_corrupted: bool = models.BooleanField(default=False)

    start_time = models.DateTimeField()
    stop_time = models.DateTimeField(null=True, blank=True)

    def clear_analysis_data(self):
        # Remove existing analysis data including endpoint data.
        for endpoint in self.ptpendpoint_set.all():
            endpoint.clear_analysis_data()
        self.analysislogrecord_set.all().delete()

        self.is_processed = False
        self.is_corrupted = False
        self.save()

    def log_analyze(self, message: str, level: LogLevel = LogLevel.INFO):
        """Save a log message for the analysis run to the database."""
        from ptp_perf.models.analysis_logrecord import AnalysisLogRecord
        logging.log(level, message)
        log_record = AnalysisLogRecord(
            profile=self,
            level=level,
            message=message,
            timestamp=get_server_datetime(),
        )
        log_record.save()


    @property
    def benchmark(self) -> "Benchmark":
        from ptp_perf.registry.benchmark_db import BenchmarkDB
        try:
            return BenchmarkDB.get(self.benchmark_id)
        except KeyError:
            return None

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

    @property
    def cluster(self) -> "Cluster":
        import ptp_perf.config as config
        return config.clusters.get(self.cluster_id)

    @property
    def duration(self):
        return self.stop_time - self.start_time if self.stop_time is not None and self.start_time is not None else None

    @property
    def estimated_time_remaining(self):
        return max(self.start_time + self.benchmark.duration - get_server_datetime(), timedelta(seconds=0))

    def __str__(self):
        return f"P{self.id} {self.benchmark} {self.vendor}"

    def analysis_log_full(self, separator="\n"):
        return str_join((record.message for record in self.analysislogrecord_set.all()), separator)

    class Meta:
        app_label = 'app'

    def export_as_json(self):
        """Export the profile to a JSON string."""
        profile_as_dict = model_to_dict(self)
        profile_as_dict["benchmark"] = dataclasses.asdict(self.benchmark)
        profile_as_dict["vendor"] = dataclasses.asdict(self.vendor)
        profile_as_dict["cluster"] = dataclasses.asdict(self.cluster) if self.cluster is not None else None
        profile_as_dict["endpoints"] = [endpoint.export_as_dict() for endpoint in self.ptpendpoint_set.all()]

        return json.dumps(profile_as_dict, cls=ModelJSONEncoder, indent=4)
