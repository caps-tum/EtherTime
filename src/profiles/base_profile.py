import copy
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Self, Optional, Literal, Dict

import pandas as pd
from pydantic import RootModel

from profiles.benchmark import Benchmark
from profiles.data_container import SummaryStatistics, Timeseries
from util import PathOrStr
from vendor.vendor import Vendor


class ProfileType:
    RAW = "raw"
    PROCESSED = "processed"

@dataclass(kw_only=True)
class BaseProfile:
    id: str
    benchmark: Benchmark
    vendor_id: str
    profile_type: Literal["raw", "processed"]
    machine_id: Optional[str]
    start_time: datetime = field(default_factory=lambda: datetime.now())

    summary_statistics: Optional[SummaryStatistics] = None
    time_series: Optional[Timeseries] = None
    raw_data: Optional[Dict[str, Optional[str]]] = None

    _file_path: Optional[str] = None

    def dump(self) -> str:
        return RootModel[type(self)](self).model_dump_json(indent=4)

    @classmethod
    def load(cls, filename: PathOrStr) -> Self:
        file_path = Path(filename)
        instance = cls.load_str(file_path.read_text())
        instance._file_path = str(file_path)
        return instance

    @classmethod
    def load_str(cls, json: str) -> Self:
        return RootModel[cls].model_validate_json(json).root

    def save(self, filename: PathOrStr = None):
        if filename is None:
            filename = self.filename
        Path(filename).write_text(self.dump())

    @staticmethod
    def template_from_existing(raw_profile: "BaseProfile", new_type: str) -> "BaseProfile":
        new_profile = copy.deepcopy(raw_profile)
        new_profile.profile_type = new_type
        new_profile.raw_data = None
        new_profile.time_series = None
        new_profile.summary_statistics = None
        return new_profile


    @property
    def filename(self):
        return (f"{self.id}"
                f"-{self.vendor}"
                f"-{self.profile_type}"
                f"-{self.machine_id}"
                f".json")

    @property
    def vendor(self) -> Vendor:
        from vendor.registry import VendorDB
        return VendorDB.get(self.vendor_id)

    @staticmethod
    def format_id_timestamp(timestamp: datetime):
        return timestamp.strftime('%Y-%m-%d-%H-%M-%S')

    def set_timeseries_data(self, timestamps: pd.Series, clock_offsets: pd.Series, normalize_time : bool = True, resample: timedelta = None) -> Self:
        if self.time_series is not None:
            raise RuntimeError("Tried to insert time series data into profile by profile already has time series data.")

        self.time_series = Timeseries.from_series(
            timestamps, clock_offsets, normalize_time=normalize_time, resample=resample,
        )
        self.summary_statistics = self.time_series.summarize()

        return self
