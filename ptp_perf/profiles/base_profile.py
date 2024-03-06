import copy
import logging
import typing
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Self, Optional, Literal, Dict

import pandas as pd
from pydantic import RootModel

from ptp_perf import constants
from ptp_perf.config import Configuration
from ptp_perf.profiles.analysis import detect_clock_step, detect_clock_convergence
from ptp_perf.profiles.benchmark import Benchmark
from ptp_perf.profiles.data_container import SummaryStatistics, Timeseries, COLUMN_CLOCK_DIFF, ConvergenceStatistics, \
    COLUMN_PATH_DELAY, COLUMN_TIMESTAMP_INDEX
from ptp_perf.util import PathOrStr

if typing.TYPE_CHECKING:
    from ptp_perf.vendor.vendor import Vendor


class ProfileType:
    RAW = "raw"
    PROCESSED = "processed"
    PROCESSED_CORRUPT = "processed-corrupt"
    AGGREGATED = "aggregated"

class ProfileTags:
    # Load
    CATEGORY_CONFIGURATION = "category_configuration"
    CATEGORY_FAULT = "category_fault"
    CATEGORY_LOAD = "category_load"

    # Component
    COMPONENT_CPU = "component_cpu"
    COMPONENT_NET = "component_net"

    # Isolation
    ISOLATION_UNPRIORITIZED = "isolation_unprioritized"
    ISOLATION_PRIORITIZED = "isolation_prioritized"
    ISOLATION_ISOLATED = "isolation_isolated"

    # Fault types
    FAULT_SOFTWARE = "fault_software"
    FAULT_HARDWARE = "fault_hardware"

    # Fault locations
    FAULT_LOCATION_SWITCH = "fault_location_switch"
    FAULT_LOCATION_SLAVE = "fault_location_slave"
    FAULT_LOCATION_MASTER = "fault_location_master"

    # Configuration Settings
    CONFIGURATION_INTERVAL = "configuration_interval"


@dataclass(kw_only=True)
class BaseProfile:
    id: str
    benchmark: Benchmark
    vendor_id: str
    profile_type: Literal["raw", "processed", "processed-corrupt", "aggregated"]
    machine_id: Optional[str]
    configuration: Optional[Configuration] = None
    start_time: datetime = field(default_factory=lambda: datetime.now())

    summary_statistics: Optional[SummaryStatistics] = None
    time_series: Optional[Timeseries] = None

    convergence_statistics: Optional[ConvergenceStatistics] = None
    time_series_unfiltered: Optional[Timeseries] = None
    raw_data: Optional[Dict[str, Optional[str]]] = field(default_factory=dict)

    success: Optional[bool] = None
    log: Optional[str] = None

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
            filename = self.file_path
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.dump())

    @staticmethod
    def template_from_existing(raw_profile: "BaseProfile", new_type: str) -> "BaseProfile":
        new_profile = copy.deepcopy(raw_profile)
        new_profile.profile_type = new_type
        new_profile.raw_data.clear()
        new_profile.time_series = None
        new_profile.summary_statistics = None
        return new_profile


    @property
    def filename(self) -> str:
        return f"{self.filename_base}.json"

    @property
    def file_path(self):
        return self.get_file_path()

    def get_file_path(self, profile_type: str = None, machine_id: str = None) -> Path:
        if profile_type is None:
            profile_type = self.profile_type
        if machine_id is None:
            machine_id = self.machine_id

        return self.storage_base_path.joinpath(profile_type).joinpath(f"{machine_id}.json")

    @property
    def file_path_relative(self):
        return self.file_path.relative_to(constants.MEASUREMENTS_DIR)

    @property
    def vendor(self) -> "Vendor":
        from ptp_perf.vendor.registry import VendorDB
        return VendorDB.get(self.vendor_id)

    @staticmethod
    def format_id_timestamp(timestamp: datetime):
        return timestamp.strftime('%Y-%m-%d--%H-%M')

    def get_title(self, extra_info: str = None):
        return f"{self.benchmark.name} ({self.vendor.name}" + (f", {extra_info})" if extra_info is not None else ")")

    def __str__(self):
        return self.id


    def check_dependent_file_needs_update(self, other: Path):
        try:
            return other.stat().st_mtime < self.file_path.stat().st_mtime
        except FileNotFoundError:
            if not other.exists():
                return True
            if not self.file_path.exists():
                raise RuntimeError(f"Cannot check whether dependent file needs update when original file does not exist: {self.file_path}")

    def memory_usage(self):
        return (self.time_series.memory_usage() if self.time_series is not None else 0) + (self.time_series_unfiltered.memory_usage() if self.time_series_unfiltered is not None else 0)
