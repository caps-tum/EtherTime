from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, Union

import numpy as np
import pandas as pd
from django.db.models import QuerySet
from pandas import MultiIndex

from ptp_perf.machine import Machine, Cluster
from ptp_perf.models import Sample, PTPEndpoint, PTPProfile
from ptp_perf.models.endpoint import TimeNormalizationStrategy
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.models.exceptions import NoDataError
from ptp_perf.profiles.benchmark import Benchmark
from ptp_perf.utilities import units
from ptp_perf.vendor.vendor import Vendor


@dataclass
class SampleQuery:
    benchmark: Optional[Benchmark] = None
    vendor: Optional[Vendor] = None
    cluster: Optional[Cluster] = None
    machine: Optional[Union[Machine, str]] = None
    endpoint_type: Optional[EndpointType] = None

    profile: Optional[PTPProfile] = None

    converged_only: bool = True
    remove_clock_step: bool = True
    normalize_time: TimeNormalizationStrategy = TimeNormalizationStrategy.CONVERGENCE

    timestamp_merge_append: bool = True
    timestamp_merge_gap: timedelta = timedelta(seconds=1)

    def run(self, sample_type: Sample.SampleType):
        endpoints = self.get_endpoint_query().all()

        data = [
            endpoint.load_samples_to_series(
                sample_type,
                converged_only=self.converged_only, remove_clock_step=self.remove_clock_step,
                normalize_time=self.normalize_time,
            ) for endpoint in endpoints
        ]

        if len(data) == 0:
            raise NoDataError("No data found for query.")

        # Cannot use None in data
        if any(data_series is None for data_series in data):
            raise NoDataError("Endpoint in query returned no data.")

        result = pd.concat(
            data,
            keys=[endpoint.id for endpoint in endpoints],
            names=["endpoint_id"]
        )

        if self.timestamp_merge_append:
            next_starting_timestamp = timedelta(seconds=0)
            for label, group in result.groupby("endpoint_id"):
                timestamp_index = group.index.get_level_values("timestamp")
                timestamp_index += next_starting_timestamp
                # TODO: Actually set the index
                next_starting_timestamp = timestamp_index.max() + self.timestamp_merge_gap


        return result

    def get_endpoint_query(self) -> QuerySet[PTPEndpoint]:
        # Don't allow unprocessed or corrupted.
        endpoint_query = PTPEndpoint.objects.filter(
            profile__is_processed=True, profile__is_corrupted=False,
        )

        if self.benchmark is not None:
            endpoint_query = endpoint_query.filter(profile__benchmark_id=self.benchmark.id)
        if self.vendor is not None:
            endpoint_query = endpoint_query.filter(profile__vendor_id=self.vendor.id)
        if self.cluster is not None:
            endpoint_query = endpoint_query.filter(profile__cluster_id=self.cluster.id)
        if self.machine is not None:
            endpoint_query = endpoint_query.filter(machine_id=self.machine.id if isinstance(self.machine, Machine) else self.machine)
        if self.endpoint_type is not None:
            endpoint_query = endpoint_query.filter(endpoint_type=self.endpoint_type)

        if self.profile is not None:
            endpoint_query = endpoint_query.filter(profile_id=self.profile.id)

        return endpoint_query

@dataclass
class QueryPostProcessor:
    data: pd.Series

    def segment_and_align(self, timestamps: pd.Series, wrap: timedelta = None):
        assert timestamps.is_monotonic_increasing

        new_data: pd.Series = self.data.copy()

        closest_cut = pd.Series(timestamps, index=timestamps).reindex(new_data.index.get_level_values("timestamp"), method='nearest')

        # segments = np.searchsorted(timestamps, new_data.index.get_level_values("timestamp"))
        # # The data before the first cut will be aligned to the first cut resulting in negative values
        # segments = (segments - 1).clip(0)

        new_timestamps = new_data.index.levels[-1] - closest_cut

        if wrap is not None:
            wrap_ns = int(wrap.total_seconds() * units.NANOSECONDS_IN_SECOND)
            wrap_half_interval = (wrap_ns // 2)
            # Move values from [-half_interval, half_interval] to [0, interval], apply modulo, move back.
            new_timestamps = (np.mod(new_timestamps.astype(np.int64) + wrap_half_interval, wrap_ns) - wrap_half_interval).astype("timedelta64[ns]")

        cut_index = np.searchsorted(timestamps, closest_cut)
        new_data = new_data.set_axis(MultiIndex.from_arrays((cut_index, new_timestamps), names=("cut_index", "timestamp")))

        # for label, group in new_data.groupby(segments):
        #     group_timestamps = group.index.get_level_values("timestamp")
        #     group_timestamps -= timestamps[max(0, label - 1)]

        return new_data
