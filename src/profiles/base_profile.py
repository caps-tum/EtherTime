import copy
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Self, Optional, Literal, Dict, List

import numpy as np
import pandas as pd
from pydantic import RootModel

import constants
from profiles.benchmark import Benchmark
from profiles.data_container import SummaryStatistics, Timeseries, COLUMN_CLOCK_DIFF, ConvergenceStatistics, \
    COLUMN_PATH_DELAY
from util import PathOrStr
from vendor.vendor import Vendor


class ProfileType:
    RAW = "raw"
    PROCESSED = "processed"
    PROCESSED_CORRUPT = "processed-corrupt"

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
    profile_type: Literal["raw", "processed", "processed-corrupt"]
    machine_id: Optional[str]
    start_time: datetime = field(default_factory=lambda: datetime.now())

    summary_statistics: Optional[SummaryStatistics] = None
    time_series: Optional[Timeseries] = None

    convergence_statistics: Optional[ConvergenceStatistics] = None
    time_series_unfiltered: Optional[Timeseries] = None
    raw_data: Optional[Dict[str, Optional[str]]] = None

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
        return f"{self.machine_id}.json"

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
        return timestamp.strftime('%Y-%m-%d-%H-%M-%S')

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
        Timeseries.check_monotonic_index(result_frame)

        # Do some data post-processing to improve quality.

        # Step 1: Remove the first big clock step.

        # Remove any beginning zero values (no clock_difference information yet) from start
        # (first non-zero value makes cumulative sum >= 0)
        crop_condition = (result_frame[COLUMN_CLOCK_DIFF] != 0).cumsum()
        result_frame = result_frame[crop_condition != 0]

        # First, detect the clock step (difference >= 1 second).
        first_difference = result_frame[COLUMN_CLOCK_DIFF].diff().abs()
        clock_steps = first_difference[first_difference >= 1]
        if len(clock_steps) > 1:
            raise RuntimeError(f"Found more than one clock step in timeseries profile: {clock_steps}")
        elif len(clock_steps) == 0:
            logging.warning(f"No clock step found in profile of length {len(result_frame)}.")
            clock_step_time = timedelta()
            clock_step_magnitude = 0
        else:
            clock_step_time = clock_steps.index[0]
            clock_step_magnitude = clock_steps.values[0]
            # The clock step should occur in the first minute and has a magnitude of 1 minute,
            # thus should occur before timestamp 2 minutes.
            if not (50 <= clock_step_magnitude <= 70):
                logging.warning(f"The clock step was not of a magnitude close to 1 minute: {clock_step_magnitude}")
            if clock_step_time >= timedelta(minutes=2):
                logging.warning(f"The clock step was not within the first 2 minutes of runtime: {clock_steps}")

        # Now crop after clock step
        logging.debug(f"Clock step at {clock_step_time}: {clock_step_magnitude}")
        result_frame = result_frame[result_frame.index > clock_step_time]

        # If we need to resample, do it now
        # This needs to happen after determining the clock step as the "missing values" that occur because of the clock
        # step will insert NaN into the series (even though they are not really missing)
        if resample is not None:
            result_frame = result_frame.resample(resample).mean()


        series_with_convergence = Timeseries.from_series(result_frame)
        self.time_series_unfiltered = series_with_convergence

        # Detect when the clock is synchronized and crop the convergence.
        # We say that the signal is converged when there are both negative and positive offsets within the window.
        window_centered = 10
        window_converged = 60
        rolling_data = series_with_convergence.clock_diff.rolling(window=window_centered, center=True)
        centered: pd.Series = (rolling_data.min() < 0) & (rolling_data.max() > 0)
        converged: pd.Series = centered.rolling(window=window_converged, center=True).median().apply(np.floor)

        # Fill the NA values that we have at the boundaries
        # Not optimal, this might also fill N/A values somewhere in the center.
        converged.ffill(inplace=True)
        converged.bfill(inplace=True)

        convergence_changes = converged[converged.diff() != 0]

        # Initial convergence point
        # This is the first point where the converged value becomes 1.0
        convergence_time = converged[converged == 1].index.min()

        # Once we converge, we should stay converged.
        minimum_convergence_time = timedelta(seconds=1)
        if not converged.any():
            logging.warning(f"Clock never converged for profile {self.id}.")
            convergence_time = None
        if converged.isna().all():
            logging.warning(f"Profile too short, convergence test resulted in only N/A values.")
            convergence_time = None

        if convergence_time is not None:

            if convergence_time < minimum_convergence_time:
                logging.warning(f"Convergence too fast: {convergence_time}. Assuming 1 second.")
                convergence_time = minimum_convergence_time

            remaining_benchmark_time = result_frame.index.max() - convergence_time
            if remaining_benchmark_time < self.benchmark.duration * 0.75:
                logging.warning(f"Cropping of convergence zone resulted in a low remaining benchmark data time of {remaining_benchmark_time}")

            if not converged.is_monotonic_increasing:
                # The first zero value is the initial setting, thus subtract 1.
                num_diverges = len(convergence_changes[convergence_changes == 0]) - 1
                convergence_after_convergence_time = converged[converged.index > convergence_time]
                if len(convergence_after_convergence_time) == 0:
                    logging.warning(f"No convergence data after convergence time of {convergence_after_convergence_time}")
                else:
                    clock_diverged_ratio = len(convergence_after_convergence_time[convergence_after_convergence_time == 0]) / len(convergence_after_convergence_time)
                    logging.warning(f"Clock diverged {num_diverges}x after converging ({clock_diverged_ratio * 100:.0f}% of samples in diverged state).")



            # Create some convergence statistics
            convergence_series = result_frame[result_frame.index <= convergence_time]

            convergence_max_offset = convergence_series[COLUMN_CLOCK_DIFF].abs().max()
            if math.isnan(convergence_max_offset):
                logging.warning("No convergence data on profile, convergence was instant.")
                convergence_max_offset = 0

            if convergence_time.total_seconds() == 0:
                raise RuntimeError("Converged in 0 seconds?")

            self.convergence_statistics = ConvergenceStatistics(
                convergence_time=convergence_time,
                convergence_max_offset=convergence_max_offset,
                convergence_rate=convergence_max_offset / convergence_time.total_seconds()
            )

            # Now create the actual data
            result_frame = result_frame[result_frame.index > convergence_time]
            series_without_convergence = Timeseries.from_series(result_frame)
            self.time_series = series_without_convergence
            self.summary_statistics = self.time_series.summarize()

        else:
            # This profile is probably corrupt.
            self.profile_type = ProfileType.PROCESSED_CORRUPT
            logging.warning("Profile marked as corrupt.")

        return self
