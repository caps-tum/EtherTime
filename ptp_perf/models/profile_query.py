from dataclasses import dataclass, field
from typing import List, Iterable, Optional, Union

from django.db.models import QuerySet

from ptp_perf.machine import Cluster
from ptp_perf.models import PTPProfile
from ptp_perf.profiles.benchmark import Benchmark
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.vendor.registry import VendorDB
from ptp_perf.vendor.vendor import Vendor


@dataclass
class ProfileQuery:
    benchmark: Optional[Benchmark] = None
    vendor: Optional[Vendor] = None
    vendor_analyzed_only: bool = True
    cluster: Optional[Cluster] = None
    is_processed: bool = True
    filter_corrupted: bool = True
    tags: List[str] = field(default_factory=list)


    def run(self) -> List[PTPProfile]:
        query = PTPProfile.objects

        if self.is_processed:
            query = query.filter(is_processed=True)
        if self.filter_corrupted:
            query = query.filter(is_corrupted=False)

        if self.benchmark:
            query = query.filter(benchmark_id=self.benchmark.id)

        if self.vendor:
            query = query.filter(vendor_id=self.vendor.id)

        if self.vendor_analyzed_only:
            query = query.filter(vendor_id__in=VendorDB.ANALYZED_VENDOR_IDS)

        if self.cluster:
            query = query.filter(cluster_id=self.cluster.id)

        benchmarks_from_tags = [benchmark for benchmark in BenchmarkDB.all() if all(tag in benchmark.tags for tag in self.tags)]
        query = query.filter(benchmark_id__in=[benchmark.id for benchmark in benchmarks_from_tags])
        return list(query)

    def run_fetch_single(self) -> PTPProfile:
        return self.run().get()
