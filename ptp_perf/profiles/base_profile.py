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
    def filename_base(self) -> str:
        return f"{self.machine_id}"

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
    def storage_base_path(self) -> Path:
        return self.benchmark.storage_base_path.joinpath(self.vendor.id).joinpath(self.id)

    def get_chart_timeseries_path(self, convergence_included: bool = False) -> Path:
        suffix = "" if not convergence_included else "-convergence"
        return self.storage_base_path.joinpath("timeseries").joinpath(f"{self.filename_base}{suffix}.png")

    @property
    def vendor(self) -> "Vendor":
        from ptp_perf.vendor.registry import VendorDB
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

        # Basic sanity checks, no duplicate timestamps
        if not timestamps.is_unique:
            value_counts = timestamps.value_counts()
            duplicate_timestamps = value_counts[value_counts != 1]
            raise RuntimeError(f"Timestamps not unique:\n{duplicate_timestamps}")
        if not timestamps.is_monotonic_increasing:
            raise RuntimeError("Timestamps not monotonically increasing.")

        # Normalize time: Move the origin to the epoch
        timestamps = timestamps - timestamps.min()

        result_frame = pd.DataFrame(
            data={
                COLUMN_CLOCK_DIFF: clock_offsets.reset_index(drop=True),
                COLUMN_PATH_DELAY: path_delays.reset_index(drop=True)
            }
        )
        result_frame.set_index(timestamps, drop=True, inplace=True)
        result_frame.index.set_names(COLUMN_TIMESTAMP_INDEX, inplace=True)
        entire_series = Timeseries.from_series(result_frame)
        entire_series.validate(maximum_allowable_time_jump=timedelta(minutes=1, seconds=10))

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

    def create_timeseries_charts(self, force_regeneration: bool = False):
        from charts.timeseries_chart import TimeseriesChart

        # We create multiple charts:
        # one only showing the filtered data and one showing the entire convergence trajectory
        if self.time_series is not None:
            output_path = self.get_chart_timeseries_path()
            if self.check_dependent_file_needs_update(output_path) or force_regeneration:
                chart = TimeseriesChart(
                    title=self.get_title(),
                    summary_statistics=self.summary_statistics,
                )
                chart.add_path_delay(self.time_series)
                chart.add_clock_difference(self.time_series)
                chart.save(output_path, make_parent=True)

        if self.time_series_unfiltered is not None:
            output_path = self.get_chart_timeseries_path(convergence_included=True)
            if self.check_dependent_file_needs_update(output_path) or force_regeneration:
                chart_convergence = TimeseriesChart(
                    title=self.get_title("with Convergence"),
                    summary_statistics=self.convergence_statistics,
                )
                chart_convergence.add_path_delay(self.time_series_unfiltered)
                chart_convergence.add_clock_difference(self.time_series_unfiltered)
                if self.convergence_statistics is not None:
                    chart_convergence.add_boundary(
                        chart_convergence.axes[0], self.convergence_statistics.convergence_time
                    )
                chart_convergence.save(output_path, make_parent=True)

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
