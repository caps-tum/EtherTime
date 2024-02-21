import copy
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Self, Optional, Literal, Dict

import pandas as pd
from pydantic import RootModel

import constants
from profiles.analysis import detect_clock_step, detect_clock_convergence
from profiles.benchmark import Benchmark
from profiles.data_container import SummaryStatistics, Timeseries, COLUMN_CLOCK_DIFF, ConvergenceStatistics, \
    COLUMN_PATH_DELAY
from util import PathOrStr
from vendor.vendor import Vendor


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

    # Configuration Settings
    CONFIGURATION_INTERVAL = "configuration_interval"


@dataclass(kw_only=True)
class BaseProfile:
    id: str
    benchmark: Benchmark
    vendor_id: str
    profile_type: Literal["raw", "processed", "processed-corrupt", "aggregated"]
    machine_id: Optional[str]
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
    def filename_base(self) -> str:
        return f"{self.machine_id}"

    @property
    def file_path(self):
        return self.storage_base_path.joinpath(self.profile_type).joinpath(self.filename)

    @property
    def file_path_relative(self):
        return self.file_path.relative_to(constants.MEASUREMENTS_DIR)

    @property
    def storage_base_path(self) -> Path:
        return constants.MEASUREMENTS_DIR.joinpath(self.benchmark.id).joinpath(self.vendor.id).joinpath(self.id)

    @property
    def vendor(self) -> Vendor:
        from vendor.registry import VendorDB
        return VendorDB.get(self.vendor_id)

    @staticmethod
    def format_id_timestamp(timestamp: datetime):
        return timestamp.strftime('%Y-%m-%d--%H-%M')

    def get_title(self, extra_info: str = None):
        return f"{self.benchmark.name} ({self.vendor.name}" + (f", {extra_info})" if extra_info is not None else ")")

    def process_timeseries_data(self, timestamps: pd.Series, clock_offsets: pd.Series, path_delays: pd.Series, resample: timedelta = None) -> Self:
        if self.time_series is not None:
            raise RuntimeError("Tried to insert time series data into profile by profile already has time series data.")
        if not (pd.api.types.is_datetime64_dtype(timestamps.dtype) or pd.api.types.is_timedelta64_dtype(timestamps.dtype)):
            raise RuntimeError(f"Received a time series the is not a datetime64 (type: {timestamps.dtype}).")

        # Normalize time: Move the origin to the epoch
        timestamps = timestamps - timestamps.min()

        result_frame = pd.DataFrame(
            data={
                COLUMN_CLOCK_DIFF: clock_offsets.reset_index(drop=True),
                COLUMN_PATH_DELAY: path_delays.reset_index(drop=True)
            }
        )
        result_frame.set_index(timestamps, drop=True, inplace=True)
        entire_series = Timeseries.from_series(result_frame)
        entire_series.validate(maximum_time_jump=timedelta(minutes=1, seconds=10))

        # Do some data post-processing to improve quality.

        # Step 1: Remove the first big clock step.

        # Remove any beginning zero values (no clock_difference information yet) from start
        # (first non-zero value makes cumulative sum >= 0)
        crop_condition = (result_frame[COLUMN_CLOCK_DIFF] != 0).cumsum()
        result_frame = result_frame[crop_condition != 0]


        detected_clock_step = detect_clock_step(result_frame)
        # Now crop after clock step
        logging.debug(f"Clock step at {detected_clock_step.time}: {detected_clock_step.magnitude}")
        result_frame = result_frame[result_frame.index > detected_clock_step.time]

        # If we need to resample, do it now
        # This needs to happen after determining the clock step as the "missing values" that occur because of the clock
        # step will insert NaN into the series (even though they are not really missing)
        if resample is not None:
            result_frame = result_frame.resample(resample).mean()

        series_with_convergence = Timeseries.from_series(result_frame)
        series_with_convergence.validate()
        self.time_series_unfiltered = series_with_convergence

        minimum_convergence_time = timedelta(seconds=1)
        detected_clock_convergence = detect_clock_convergence(series_with_convergence, minimum_convergence_time)

        if detected_clock_convergence is not None:

            remaining_benchmark_time = result_frame.index.max() - detected_clock_convergence.time
            if remaining_benchmark_time < self.benchmark.duration * 0.75:
                logging.warning(f"Cropping of convergence zone resulted in a low remaining benchmark data time of {remaining_benchmark_time}")

            # Create some convergence statistics
            convergence_series = result_frame[result_frame.index <= detected_clock_convergence.time]
            self.convergence_statistics = ConvergenceStatistics.from_convergence_series(detected_clock_convergence, convergence_series)

            # Now create the actual data
            result_frame = result_frame[result_frame.index > detected_clock_convergence.time]
            self.time_series = Timeseries.from_series(result_frame)
            self.time_series.validate()
            self.summary_statistics = self.time_series.summarize()

        else:
            # This profile is probably corrupt.
            self.profile_type = ProfileType.PROCESSED_CORRUPT
            logging.warning("Profile marked as corrupt.")

        return self

    def __str__(self):
        return self.id


