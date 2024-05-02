from dataclasses import dataclass
from typing import List

import pandas as pd
from pandas.tests.scalar import timedelta

from ptp_perf.models import Sample, PTPEndpoint, PTPProfile
from ptp_perf.models.sample_query import SampleQuery
from ptp_perf.util import unpack_one_value


@dataclass
class Fault:
    endpoint: PTPEndpoint
    start: timedelta
    end: timedelta

    @staticmethod
    def from_profile(profile: PTPProfile) -> List["Fault"]:
        faults: List[Sample] = Sample.objects.filter(
            endpoint__profile_id=profile.id, sample_type=Sample.SampleType.FAULT
        )
        parsed_faults = []
        fault_start = None
        for id, fault in enumerate(faults):
            if id % 2 == 0:
                assert fault.value == 1
                fault_start = fault
            else:
                assert fault.value == 0
                assert fault.endpoint_id == fault_start.endpoint_id
                parsed_faults.append(
                    Fault(
                        fault.endpoint,
                        fault_start.timestamp - profile.start_time, fault.timestamp - profile.start_time
                    )
                )
        return parsed_faults

    @staticmethod
    def from_query(query: SampleQuery) -> List["Fault"]:
        frame = query.run(Sample.SampleType.FAULT).reset_index()

        faults = []
        for endpoint_id, endpoint_faults in frame.groupby("endpoint_id"):
            if len(endpoint_faults) < 2:
                raise RuntimeError(
                    f"Cannot parse faults from frame of length: {len(endpoint_faults)}\n{endpoint_faults}")
            if len(endpoint_faults) > 2:
                raise NotImplementedError(
                    f"Sorry, too many faults ({len(endpoint_faults)} != 2 samples)\n{endpoint_faults}"
                )

            faults.append(
                Fault(
                    endpoint=PTPEndpoint.objects.get(id=endpoint_id),
                    start=unpack_one_value(endpoint_faults[endpoint_faults['value'] == 1]['timestamp']),
                    end=unpack_one_value(endpoint_faults[endpoint_faults['value'] == 0]['timestamp'])
                )
            )
        return faults
