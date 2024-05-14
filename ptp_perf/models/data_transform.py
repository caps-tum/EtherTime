from dataclasses import dataclass, field
from typing import Union, Iterable, List, Callable, Type, Optional

import pandas as pd
from django.db.models import Model, Field

from ptp_perf.models import PTPEndpoint, BenchmarkSummary
from ptp_perf.utilities.pandas_utilities import frame_column
from ptp_perf.vendor.registry import VendorDB

SUPPORTED_MODELS = Union[PTPEndpoint, BenchmarkSummary]

class DataQuerySort:
    ENDPOINT_BY_VENDOR = lambda endpoint: VendorDB.ANALYZED_VENDORS.index(endpoint.profile.vendor)

class DataQueryMelt:
    VALUES_CLOCK_DIFF_QUANTILES = [
        frame_column(PTPEndpoint.clock_diff_p05),
        frame_column(PTPEndpoint.clock_diff_median),
        frame_column(PTPEndpoint.clock_diff_p95),
    ]

@dataclass
class DataTransform:
    expansions: List[Union[Model, Field]] = field(default_factory=list)

    # Sorting function
    sort_key: Optional[Callable] = None

    # Melting (merging columns)
    use_melt: bool = False
    melt_id_vars: List[str] = None
    melt_value_vars: List[str] = None

    def run(self, input_data: Iterable[SUPPORTED_MODELS]) -> pd.DataFrame:
        frame = self.load_to_frame(self.sort_objects(input_data))
        if self.use_melt:
            frame = self.melt(frame)
        return frame

    def sort_objects(self, objects: Iterable[SUPPORTED_MODELS]) -> List[SUPPORTED_MODELS]:
        if self.sort_key is None:
            return list(objects)

        return [
            object_instance for object_instance in
            sorted(objects, key=self.sort_key)
        ]

    def load_to_frame(self, objects: Iterable[SUPPORTED_MODELS]):
        expansion_names = [frame_column(expansion, foreign_key_use_id=False) for expansion in self.expansions]
        return pd.DataFrame(
            data=(
                {
                    key: value
                    for key, value in object_instance.__dict__.items()
                    if not key.startswith("_")
                } | {
                    f"{expansion}__{key}": value
                    for expansion in expansion_names
                    for key, value in object_instance.__getattribute__(expansion).__dict__.items()
                    if not key.startswith("_")
                }
                for object_instance in objects
            )
        )

    def melt(self, frame: pd.DataFrame) -> pd.DataFrame:
        return frame.melt(
            id_vars=self.melt_id_vars,
            value_vars=self.melt_value_vars,
        )
