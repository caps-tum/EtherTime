import math
import json
import logging
import re
import typing
from datetime import timedelta, datetime
from enum import StrEnum
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
from django.db import models
from django.db.models import CASCADE
from django.forms import model_to_dict
from pandas.core.dtypes.common import is_numeric_dtype

from ptp_perf import config
from ptp_perf.machine import Machine, Cluster, MachineClientType
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.models.exceptions import NoDataError
from ptp_perf.models.loglevel import LogLevel
from ptp_perf.models.profile import PTPProfile
from ptp_perf.profiles.analysis import detect_clock_step, detect_clock_convergence
from ptp_perf.profiles.benchmark import Benchmark
from ptp_perf.profiles.data_container import Timeseries, ConvergenceStatistics
from ptp_perf.util import unpack_one_value
from ptp_perf.utilities import units, psutil_utilities
from ptp_perf.utilities.django_utilities import TimeFormatFloatField, PercentageFloatField, DataFormatFloatField, \
    GenericEngineeringFloatField, TemperatureFormatFloatField, FrequencyFormatFloatField
from ptp_perf.utilities.serialization import ModelJSONEncoder

if typing.TYPE_CHECKING:
    from ptp_perf.models.sample import Sample
    from ptp_perf.charts.timeseries_chart import TimeseriesChart

class ProfileCorruptError(Exception):
    pass

class TimeNormalizationStrategy(StrEnum):
    NONE = "none"
    PROFILE_START = "profile_start"
    CLOCK_STEP = "clock_step"
    CONVERGENCE = "convergence"

COLUMN_TIMESTAMP_INDEX = "timestamp"

class PTPEndpoint(models.Model):
    id = models.AutoField(primary_key=True)

    profile: PTPProfile = models.ForeignKey(PTPProfile, on_delete=CASCADE)
    machine_id = models.CharField(max_length=255)
    """Machine ID is the unique identifier for the machine in the cluster."""
    restart_count = models.IntegerField(default=0)
    """How often the PTP process was restarted on this machine."""

    endpoint_type = models.CharField(choices=EndpointType, max_length=32, default=EndpointType.UNKNOWN)
    """The type of endpoint this is, e.g. master, slave, switch, orchestrator etc. (see EndpointType)"""

    # Summary statistics
    clock_diff_median = TimeFormatFloatField(null=True)
    """The median of the absolute clock difference between the local and the master clock."""
    clock_diff_p05 = TimeFormatFloatField(null=True)
    """The 5th percentile of the absolute clock difference between the local and the master clock."""
    clock_diff_p95 = TimeFormatFloatField(null=True)
    """The 95th percentile of the absolute clock difference between the local and the master clock."""
    path_delay_median = TimeFormatFloatField(null=True)
    """The median of the path delay estimate across the network between the local client and the master server."""
    path_delay_p05 = TimeFormatFloatField(null=True)
    """The 5th percentile of the path delay estimate across the network between the local client and the master server."""
    path_delay_p95 = TimeFormatFloatField(null=True)
    """The 95th percentile of the path delay estimate across the network between the local client and the master server."""
    path_delay_std = TimeFormatFloatField(null=True)
    """The standard deviation of the path delay estimate across the network between the local client and the master server."""

    # Missing values
    missing_samples_count = models.IntegerField(null=True)
    """How many samples are missing in the time series data, defined by the number of times that the PTP application did not output a synchronization log message within 3x the target sync interval."""
    missing_samples_percent = PercentageFloatField(null=True)
    """The percentage of missing samples in the time series data, defined by the total samples missing divided by the total time of the benchmark."""

    # Convergence statistics
    convergence_timestamp = models.DateTimeField(null=True)
    """The timestamp at which the clock difference data converged (become stable) on this endpoint."""
    convergence_duration = models.DurationField(null=True)
    """The duration of the convergence phase from starting the PTP application to the convergence timestamp."""
    convergence_max_offset = TimeFormatFloatField(null=True)
    """The maximum offset of the clock difference data during the convergence phase."""
    convergence_rate = TimeFormatFloatField(null=True)
    """The rate at which the clock difference data converged during the convergence phase, in parts per second."""

    converged_percentage = PercentageFloatField(null=True)
    """The percentage of all samples that were posted while the clock was considered stable."""
    converged_samples = models.IntegerField(null=True)
    """The number of samples posted while the clock was considered stable."""

    # Clock step
    clock_step_timestamp = models.DateTimeField(null=True)
    """The timestamp at which the initial  clock step was detected on this endpoint."""
    clock_step_magnitude = models.FloatField(null=True)
    """The magnitude of the initial clock step detected on this endpoint, should be roughly equal to the machine's initial offset set in the configuration."""

    # Fault Data
    fault_clock_diff_pre_median = TimeFormatFloatField(null=True)
    fault_clock_diff_pre_p05 = TimeFormatFloatField(null=True)
    fault_clock_diff_pre_p95 = TimeFormatFloatField(null=True)
    fault_path_delay_pre_median = TimeFormatFloatField(null=True)
    fault_path_delay_pre_p05 = TimeFormatFloatField(null=True)
    fault_path_delay_pre_p95 = TimeFormatFloatField(null=True)

    fault_clock_diff_post_median = TimeFormatFloatField(null=True)
    fault_clock_diff_post_p05 = TimeFormatFloatField(null=True)
    fault_clock_diff_post_p95 = TimeFormatFloatField(null=True)
    fault_path_delay_post_median = TimeFormatFloatField(null=True)
    fault_path_delay_post_p05 = TimeFormatFloatField(null=True)
    fault_path_delay_post_p95 = TimeFormatFloatField(null=True)

    # Fault Summaries
    fault_actual_duration = models.DurationField(null=True)
    fault_ratio_clock_diff_median = models.FloatField(null=True)
    fault_ratio_clock_diff_p95 = models.FloatField(null=True)

    fault_clock_diff_post_max = models.FloatField(null=True)
    fault_ratio_clock_diff_post_max_pre_median = models.FloatField(null=True)
    fault_clock_diff_return_to_normal_time = models.DurationField(null=True)

    fault_clock_diff_mid_max = models.FloatField(null=True)

    # Resource consumption data
    resource_profile_length: timedelta = models.DurationField(null=True)

    proc_cpu_percent = PercentageFloatField(null=True)
    proc_cpu_percent_system = PercentageFloatField(null=True)
    proc_cpu_percent_user = PercentageFloatField(null=True)
    proc_mem_uss = DataFormatFloatField(null=True)
    proc_mem_pss = DataFormatFloatField(null=True)
    proc_mem_rss = DataFormatFloatField(null=True)
    proc_mem_vms = DataFormatFloatField(null=True)
    proc_io_write_count = GenericEngineeringFloatField(null=True)
    proc_io_write_bytes = DataFormatFloatField(null=True)
    proc_io_read_count = GenericEngineeringFloatField(null=True)
    proc_io_read_bytes = DataFormatFloatField(null=True)
    proc_ctx_switches_involuntary = GenericEngineeringFloatField(null=True)
    proc_ctx_switches_voluntary = GenericEngineeringFloatField(null=True)

    sys_sensors_temperature_cpu = TemperatureFormatFloatField(null=True)
    sys_cpu_frequency = FrequencyFormatFloatField(null=True)

    sys_net_ptp_iface_bytes_sent = DataFormatFloatField(null=True)
    sys_net_ptp_iface_packets_sent = GenericEngineeringFloatField(null=True)
    sys_net_ptp_iface_bytes_received = DataFormatFloatField(null=True)
    sys_net_ptp_iface_packets_received = GenericEngineeringFloatField(null=True)
    sys_net_ptp_iface_bytes_total = DataFormatFloatField(null=True)
    sys_net_ptp_iface_packets_total = GenericEngineeringFloatField(null=True)

    def load_samples_to_series(self, sample_type: "Sample.SampleType", converged_only: bool = True,
                               remove_clock_step: bool = True, remove_clock_step_force: bool = True,
                               normalize_time: TimeNormalizationStrategy = TimeNormalizationStrategy.CONVERGENCE) -> Optional[pd.Series]:
        from ptp_perf.models import Sample
        sample_set = self.sample_set.filter(sample_type=sample_type)

        if converged_only:
            if self.convergence_timestamp is None:
                raise RuntimeError(f"Requested converged data but no convergence time is present: {self}.")
            sample_set = sample_set.filter(timestamp__gte=self.convergence_timestamp)

        if remove_clock_step:
            if self.clock_step_timestamp is None:
                if remove_clock_step_force:
                    raise RuntimeError("Requested clock step exclusion but no clock step timestamp is present.")
            else:
                sample_set = sample_set.filter(timestamp__gte=self.clock_step_timestamp)

        frame = pd.DataFrame(sample_set.values("timestamp", "value"))
        if frame.empty:
            return None
        # print(frame)
        # frame = frame.pivot(columns=["sample_type"])
        # frame[COLUMN_CLOCK_DIFF] = frame.loc[frame["sample_type"] == "CLOCK_DIFF", "value"]
        # frame = frame.set_index(["id", "endpoint_id", "timestamp", "sample_type"])["value"].unstack().reset_index()

        # frame["timestamp"] = frame["timestamp"].dt.tz_localize(None)
        series = frame.set_index("timestamp")["value"]

        if sample_type == Sample.SampleType.CLOCK_DIFF or sample_type == Sample.SampleType.PATH_DELAY:
            series *= units.NANOSECONDS_TO_SECONDS

        if normalize_time != TimeNormalizationStrategy.NONE:
            series.index -= self.get_normalization_origin(normalize_time)

        return series

    def get_normalization_origin(self, normalization_strategy):
        reference_points = {
            TimeNormalizationStrategy.PROFILE_START: self.profile.start_time,
            TimeNormalizationStrategy.CLOCK_STEP: self.clock_step_timestamp,
            TimeNormalizationStrategy.CONVERGENCE: self.convergence_timestamp,
        }
        return reference_points[normalization_strategy]

    def normalize(self, data: typing.Union[datetime, pd.Series], normalization: TimeNormalizationStrategy):
        return data - self.get_normalization_origin(normalization)


    def process_timeseries_data(self):
        from ptp_perf.models.sample import Sample

        entire_series = self.load_samples_to_series(
            Sample.SampleType.CLOCK_DIFF, converged_only=False,
            remove_clock_step=False, normalize_time=TimeNormalizationStrategy.NONE
        )
        if entire_series is None:
            return

        timestamps = entire_series.index
        if not isinstance(timestamps.dtype, pd.DatetimeTZDtype):
            raise ProfileCorruptError(f"Received a time series the is not a datetime64+tz (type: {timestamps.dtype}).")

        # Basic sanity checks, no duplicate timestamps
        if not timestamps.is_unique:
            value_counts = timestamps.value_counts()
            duplicate_timestamps = value_counts[value_counts != 1]
            raise ProfileCorruptError(f"Timestamps not unique:\n{duplicate_timestamps}")
        if not timestamps.is_monotonic_increasing:
            time_index_diff = entire_series.index.diff()
            time_rewinds = time_index_diff < timedelta(seconds=0)
            # Show some context.
            adjacent_values = pd.Series(time_rewinds).rolling(10).max().astype(bool).reset_index(drop=True)
            steps_backward = entire_series[adjacent_values]
            raise ProfileCorruptError(
                f"Timestamps not monotonically increasing:\n{steps_backward}"
            )

        # We don't normalize time automatically anymore.
        # Normalize time: Move the origin to the epoch
        # timestamps = timestamps - timestamps.min()

        Timeseries._validate_series(entire_series, maximum_allowable_time_jump=timedelta(minutes=1, seconds=10))

        # Do some data post-processing to improve quality.

        # First: calculate missing data ratios
        # Maximum gap: 3x the target sync interval.
        maximum_allowable_time_jump = timedelta(seconds=self.benchmark.sync_interval_seconds * 3)
        timeseries_gaps = self.calculate_missing_data(entire_series, maximum_allowable_time_jump)
        total_time_missing = timeseries_gaps.sum()
        self.missing_samples_count = total_time_missing.total_seconds() / self.benchmark.sync_interval_seconds
        self.missing_samples_percent = total_time_missing.total_seconds() / self.benchmark.duration.total_seconds()

        # Step 1: Remove the first big clock step.

        # Remove any beginning zero values (no clock_difference information yet) from start
        # (first non-zero value makes cumulative sum >= 0)
        crop_condition = (entire_series != 0).cumsum()
        frame_no_leading_zeros = entire_series[crop_condition != 0]

        detected_clock_step = detect_clock_step(frame_no_leading_zeros, self.benchmark.analyze_limit_permissible_clock_steps)
        self.clock_step_timestamp = detected_clock_step.time
        self.clock_step_magnitude = detected_clock_step.magnitude

        # Now crop after clock step
        self.profile.log_analyze(
            f"Clock step at {detected_clock_step.time}: {detected_clock_step.magnitude}", level=LogLevel.DEBUG
        )
        frame_no_clock_step = frame_no_leading_zeros[frame_no_leading_zeros.index > detected_clock_step.time]

        Timeseries._validate_series(frame_no_clock_step)

        minimum_convergence_time = timedelta(seconds=10)
        detected_clock_convergence = detect_clock_convergence(frame_no_clock_step, minimum_convergence_time)

        if detected_clock_convergence is None:
            raise ProfileCorruptError("No clock convergence detected.")

        remaining_benchmark_time = frame_no_clock_step.index.max() - detected_clock_convergence.timestamp
        if remaining_benchmark_time < self.benchmark.duration * 0.5:
            self.profile.log_analyze(
                f"Cropping of convergence zone resulted in a low remaining benchmark data time of {remaining_benchmark_time}",
                level=LogLevel.WARNING,
            )

        # Create some convergence statistics
        convergence_series = frame_no_clock_step[frame_no_clock_step.index <= detected_clock_convergence.timestamp]
        convergence_statistics = ConvergenceStatistics.from_convergence_series(detected_clock_convergence,
                                                                               convergence_series)
        self.convergence_timestamp = detected_clock_convergence.timestamp
        self.convergence_duration = detected_clock_convergence.duration
        self.convergence_rate = convergence_statistics.convergence_rate
        self.convergence_max_offset = convergence_statistics.convergence_max_offset
        self.converged_percentage = detected_clock_convergence.ratio_converged_samples
        self.converged_samples = detected_clock_convergence.num_converged_samples


        # Now create the actual data
        converged_series = frame_no_clock_step[frame_no_clock_step.index > detected_clock_convergence.timestamp]
        Timeseries._validate_series(converged_series)

        # self.summary_statistics = self.time_series.summarize()
        abs_clock_diff = converged_series.abs()
        self.clock_diff_median, self.clock_diff_p05, self.clock_diff_p95 = self.calculate_quantiles(abs_clock_diff)

        path_delay_values = self.load_samples_to_series(Sample.SampleType.PATH_DELAY, converged_only=True, normalize_time=TimeNormalizationStrategy.NONE)
        self.path_delay_median, self.path_delay_p05, self.path_delay_p95 = self.calculate_quantiles(path_delay_values)
        self.path_delay_std = path_delay_values.std()

        # If there was a fault, calculate fault statistics
        # We pull in faults from all locations so that every endpoint gets statistics
        try:
            # This raises nodataexception if no faults found
            faults = Sample.objects.filter(
                endpoint__profile_id=self.profile_id, sample_type=Sample.SampleType.FAULT
            )

            if len(faults) > 2:
                raise ProfileCorruptError("Cannot support multiple faults in one profile at the moment.")
            fault_start = faults.filter(value=1).get()
            fault_end = faults.filter(value=0).get()
            if fault_start.timestamp <= self.convergence_timestamp:
                raise ProfileCorruptError("Clock did not converge before the first fault.")
            if fault_start.timestamp >= fault_end.timestamp:
                raise ProfileCorruptError("Fault ended before it started?")
            if fault_end.timestamp > max(frame_no_clock_step.index):
                # TODO: Investigate fault corruption
                error_msg = f"Fault out of data range on endpoint {self} " \
                            f"Data interval: [{min(frame_no_clock_step.index)}, {max(frame_no_clock_step.index)}], " \
                            f"Fault interval: [{fault_start.timestamp}, {fault_end.timestamp}]"

                if self.profile.benchmark.fault_location == self.endpoint_type:
                    raise ProfileCorruptError(error_msg)
                else:
                    self.profile.log_analyze(error_msg, level=LogLevel.WARNING)

            pre_fault_series = abs_clock_diff[abs_clock_diff.index <= fault_start.timestamp]
            self.fault_clock_diff_pre_median, self.fault_clock_diff_pre_p05, self.fault_clock_diff_pre_p95 = (
                self.calculate_quantiles(pre_fault_series)
            )
            pre_fault_path_delay = path_delay_values[path_delay_values.index <= fault_start.timestamp]
            self.fault_path_delay_pre_median, self.fault_path_delay_pre_p05, self.fault_path_delay_pre_p95 = (
                self.calculate_quantiles(pre_fault_path_delay)
            )

            post_fault_series = abs_clock_diff[abs_clock_diff.index >= fault_end.timestamp]
            if not post_fault_series.empty:
                self.fault_clock_diff_post_median, self.fault_clock_diff_post_p05, self.fault_clock_diff_post_p95 = (
                    self.calculate_quantiles(post_fault_series)
                )
                post_fault_path_delay = path_delay_values[path_delay_values.index >= fault_end.timestamp]
                self.fault_path_delay_post_median, self.fault_path_delay_post_p05, self.fault_path_delay_post_p95 = (
                    self.calculate_quantiles(post_fault_path_delay)
                )

                self.fault_actual_duration = post_fault_series.index.min() - pre_fault_series.index.max()
                self.fault_ratio_clock_diff_median = self.fault_clock_diff_post_median / self.fault_clock_diff_pre_median
                self.fault_ratio_clock_diff_p95 = self.fault_clock_diff_post_p95 / self.fault_clock_diff_pre_p95

                self.fault_clock_diff_post_max = post_fault_series.max()
                self.fault_ratio_clock_diff_post_max_pre_median = self.fault_clock_diff_post_max / self.fault_clock_diff_pre_median

                # Calculate how long it takes to return to normal (within 2x of pre-fault median)
                post_fault_series_smoothed = post_fault_series.rolling(5).median()
                post_fault_under_2x_median = post_fault_series[
                    post_fault_series_smoothed < 2 * self.fault_clock_diff_pre_median
                ]
                if not post_fault_under_2x_median.empty:
                    self.fault_clock_diff_return_to_normal_time = post_fault_under_2x_median.index[0] - fault_end.timestamp
                else:
                    self.fault_clock_diff_return_to_normal_time = None

            mid_fault_series = abs_clock_diff[(abs_clock_diff.index > fault_start.timestamp) & (abs_clock_diff.index < fault_end.timestamp)]
            if not mid_fault_series.empty:
                self.fault_clock_diff_mid_max = mid_fault_series.max()

        except (NoDataError, Sample.DoesNotExist):
            if self.benchmark.fault_location is not None:
                raise ProfileCorruptError(f"Could not find fault for profile {self.profile} on benchmark {self.benchmark}")

        self.save()
        return self

    def _validate_series(self, series: pd.Series, maximum_allowable_time_jump: timedelta = timedelta(seconds=5)):
        # Validate shape of frame and properties
        assert is_numeric_dtype(series)
        assert series.index.is_unique, f"Series index is not unique:\n{series}"
        assert COLUMN_TIMESTAMP_INDEX in series.index.names, f"Series index does not have a timestamp level\n{series}"
        # Datetime64 with timezone is not so easy to detect.
        assert isinstance(series.index.get_level_values(COLUMN_TIMESTAMP_INDEX).dtype, pd.DatetimeTZDtype), f"Series index level timestamps is not a series of datetime64+tz.\n{series}"

        # Ensure that data is sorted chronologically.
        time_jumps = self.calculate_missing_data(series, maximum_allowable_time_jump)
        min_time_jump = time_jumps.min()
        if min_time_jump < timedelta(seconds=0):
            raise RuntimeError(
                f"Timeseries index is not monotonically increasing."
            )
        # Make sure there are no gaps in the data
        if not time_jumps.empty:
            self.profile.log_analyze(
                f"Timeseries contains {len(time_jumps)} holes "
                f"(largest hole: {time_jumps.max()}, "
                f"total: {time_jumps.sum()} = {100 * time_jumps.sum() / (series.index.max() / series.index.min()):.0f}%)",
                level=LogLevel.WARNING,
            )
        # Ensure we have sufficient data in general
        # At least 10 minutes -> At least 600 samples
        if len(series) < 600:
            self.profile.log_analyze(
                f"Timeseries contains too few data points: {len(series)}", level=LogLevel.WARNING
            )

    @staticmethod
    def calculate_missing_data(series: pd.Series, maximum_allowable_time_jump: timedelta = timedelta(seconds=5)):
        index_time_deltas = series.index.diff()
        time_jumps = index_time_deltas[index_time_deltas >= maximum_allowable_time_jump]
        return time_jumps

    @staticmethod
    def calculate_quantiles(series: pd.Series) -> Tuple[float, float, float]:
        """Order of return values: median, p05, p95"""
        return series.quantile([0.5, 0.05, 0.95]).values

    def create_timeseries_charts(self, force_regeneration: bool = False):
        from ptp_perf.charts.timeseries_chart import TimeseriesChart
        from ptp_perf.models.sample import Sample

        # We create multiple charts:
        # one only showing the filtered data and one showing the entire convergence trajectory
        if self.convergence_timestamp is not None:
            clock_diff = self.load_samples_to_series(Sample.SampleType.CLOCK_DIFF, normalize_time=TimeNormalizationStrategy.CONVERGENCE)
            path_delay = self.load_samples_to_series(Sample.SampleType.PATH_DELAY, normalize_time=TimeNormalizationStrategy.CONVERGENCE)

            if clock_diff is None or path_delay is None:
                raise NoDataError()

            output_path = self.get_chart_timeseries_path()
            # if self.check_dependent_file_needs_update(output_path) or force_regeneration:
            chart = TimeseriesChart(
                title=self.get_title(),
                # summary_statistics=SummaryStatistics.create(clock_diff, path_delay),
                ylimit_top = 0.0001,
                ylimit_top_use_always=True,
                ylimit_bottom = 0,
                # ylog=True
                legend=True,
            )
            chart.add_path_delay(path_delay)
            chart.add_clock_difference(clock_diff)
            # legend = chart.figure.legend(["Path Delay", "Path Delay", "Clock Difference"])
            # legend.
            chart.save(output_path, make_parents=True)

        if self.clock_step_timestamp is not None:
            chart_convergence = self.create_timeseries_chart_convergence()
            output_path = self.get_chart_timeseries_path(convergence_included=True)
            chart_convergence.save(output_path, make_parents=True)

    def create_timeseries_chart_convergence(self, normalization=TimeNormalizationStrategy.CLOCK_STEP) -> "TimeseriesChart":
        from ptp_perf.charts.timeseries_chart import TimeseriesChart
        from ptp_perf.models.sample import Sample
        clock_diff = self.load_samples_to_series(
            Sample.SampleType.CLOCK_DIFF,
            converged_only=False, remove_clock_step_force=False, normalize_time=normalization,
        )
        path_delay = self.load_samples_to_series(
            Sample.SampleType.PATH_DELAY,
            converged_only=False, remove_clock_step_force=False, normalize_time=normalization,
        )
        # if self.check_dependent_file_needs_update(output_path) or force_regeneration:
        chart_convergence = TimeseriesChart(
            title=self.get_title("with Convergence"),
            summary_statistics=None,
        )
        if path_delay is not None:
            chart_convergence.add_path_delay(path_delay)
        if clock_diff is not None:
            chart_convergence.add_clock_difference(clock_diff)
        if self.convergence_duration is not None:
            chart_convergence.add_boundary(
                chart_convergence.axes[0], self.normalize(self.convergence_timestamp, normalization)
            )
        return chart_convergence

    def process_fault_data(self):
        from ptp_perf.models import LogRecord, Sample
        records = LogRecord.objects.filter(source="fault-generator", endpoint__profile=self.profile).all()
        parsed_faults = 0
        for record in records:
            # We import faults either directly on the current endpoint.
            # If we are the orchestrator, then we get faults from switch2 (easier to regex match).
            # We ignore faults on switch #1 because they are the same.
            location = self.machine_id if self.machine_id != 'orchestrator' else 'switch2'
            match = re.search(
                f"Scheduled (?P<type>\S+) fault (?P<status>imminent|resolved) on ({location}).",
                record.message
            )
            if match is not None:
                sample = Sample(
                    endpoint=self,
                    timestamp=record.timestamp,
                    sample_type=Sample.SampleType.FAULT,
                    value=1 if match.group("status") == "imminent" else 0
                )
                sample.save()
                parsed_faults += 1
        if parsed_faults > 0:
            self.profile.log_analyze(f"{self} parsed {parsed_faults} fault status records.")
        return parsed_faults


    def process_system_metrics_data(self):
        from ptp_perf.models import LogRecord
        from ptp_perf.adapters.resource_monitor import ResourceMonitor
        records = LogRecord.objects.filter(
            source=ResourceMonitor.log_source, endpoint=self
        ).exclude(
            message__contains='"process": {}'
        ).order_by('id').all()

        # Check if any data available
        if len(records) != 0:
            # Sample data:
            # {
            #   "system": {
            #     "cpu_times": {
            #       "user": 5.03,
            #       "nice": 0,
            #       "system": 4.36,
            #       "idle": 105.34,
            #       "iowait": 9.22,
            #       "irq": 0,
            #       "softirq": 0,
            #       "steal": 0,
            #       "guest": 0,
            #       "guest_nice": 0
            #     },
            #     "cpu_percent": 0.2,
            #     "cpu_stats": {
            #       "ctx_switches": 100070,
            #       "interrupts": 80280,
            #       "soft_interrupts": 43078,
            #       "syscalls": 0
            #     },
            #     "cpu_freq": {
            #       "current": 2400,
            #       "min": 1500,
            #       "max": 2400
            #     },
            #     "virtual_memory": {
            #       "total": 4241719296,
            #       "available": 3903979520,
            #       "percent": 8,
            #       "used": 274235392,
            #       "free": 3632332800,
            #       "active": 377946112,
            #       "inactive": 119701504,
            #       "buffers": 33308672,
            #       "cached": 301842432,
            #       "shared": 6045696,
            #       "slab": 49577984
            #     },
            #     "disk_io_counters": {
            #       "read_count": 6814,
            #       "write_count": 521,
            #       "read_bytes": 281693696,
            #       "write_bytes": 19522048,
            #       "read_time": 19048,
            #       "write_time": 65735,
            #       "read_merged_count": 4272,
            #       "write_merged_count": 255,
            #       "busy_time": 12044
            #     },
            #     "net_io_counters": {
            #       "lo": {
            #         "bytes_sent": 12129,
            #         "bytes_recv": 12129,
            #         "packets_sent": 135,
            #         "packets_recv": 135,
            #         "errin": 0,
            #         "errout": 0,
            #         "dropin": 0,
            #         "dropout": 0
            #       },
            #       "eth0": {
            #         "bytes_sent": 4280,
            #         "bytes_recv": 1946,
            #         "packets_sent": 38,
            #         "packets_recv": 22,
            #         "errin": 0,
            #         "errout": 0,
            #         "dropin": 0,
            #         "dropout": 0
            #       },
            #       "wlan0": {
            #         "bytes_sent": 39457,
            #         "bytes_recv": 33166,
            #         "packets_sent": 190,
            #         "packets_recv": 180,
            #         "errin": 0,
            #         "errout": 0,
            #         "dropin": 0,
            #         "dropout": 0
            #       }
            #     },
            #     "sensors_temperature": {
            #       "cpu_thermal": [
            #         {
            #           "label": "",
            #           "current": 56.75,
            #           "high": null,
            #           "critical": null
            #         }
            #       ],
            #       "rp1_adc": [
            #         {
            #           "label": "",
            #           "current": 56.634,
            #           "high": null,
            #           "critical": null
            #         }
            #       ]
            #     }
            #   },
            #   "process": {
            #     "cpu_percent": 0,
            #     "num_threads": 1,
            #     "num_ctx_switches": {
            #       "voluntary": 8,
            #       "involuntary": 2
            #     },
            #     "memory_full_info": {
            #       "rss": 4194304,
            #       "vms": 11468800,
            #       "shared": 3670016,
            #       "text": 311296,
            #       "lib": 0,
            #       "data": 819200,
            #       "dirty": 0,
            #       "uss": 1212416,
            #       "pss": 1679360,
            #       "swap": 0
            #     },
            #     "io_counters": {
            #       "read_count": 33,
            #       "write_count": 5,
            #       "read_bytes": 0,
            #       "write_bytes": 0,
            #       "read_chars": 32273,
            #       "write_chars": 324
            #     },
            #     "cpu_times": {
            #       "user": 0,
            #       "system": 0,
            #       "children_user": 0,
            #       "children_system": 0,
            #       "iowait": 0
            #     }
            #   }
            # }

            # Difference data: data based on counter can be subtracted and converted into a rate where applicable.
            first_record: LogRecord = records.first()
            last_record: LogRecord = records.last()

            first_last_difference = psutil_utilities.hierarchical_apply(
                json.loads(last_record.message), json.loads(first_record.message),
                lambda x, y: x - y,
            )
            self.resource_profile_length = last_record.timestamp - first_record.timestamp
            self.proc_cpu_percent_system = first_last_difference["process"]["cpu_times"]["system"] / self.resource_profile_length.total_seconds()
            self.proc_cpu_percent_user = first_last_difference["process"]["cpu_times"]["user"] / self.resource_profile_length.total_seconds()
            self.proc_cpu_percent = self.proc_cpu_percent_system + self.proc_cpu_percent_user

            records_parsed = [json.loads(record.message) for record in records]
            self.sys_cpu_frequency = pd.Series(record["system"]["cpu_freq"]["current"] for record in records_parsed).mean()
            # The sensor is a single-element list for some reason, needs to be unpacked
            sensor_temperature_data = [
                record["system"]["sensors_temperature"] for record in records_parsed
                if len(record["system"]["sensors_temperature"]) != 0
            ]
            if len(sensor_temperature_data) != 0:
                try:
                    self.sys_sensors_temperature_cpu = pd.Series(
                        unpack_one_value(record["cpu_thermal"])["current"] for record in sensor_temperature_data
                    ).mean()
                except KeyError:
                    # On TK-1, it's of course named differently :/
                    try:
                        self.sys_sensors_temperature_cpu = pd.Series(
                            unpack_one_value(record["CPU-therm"])["current"] for record in sensor_temperature_data
                        ).mean()
                    except KeyError:
                        raise RuntimeError(f"Unknown temperature sensor set:\n{sensor_temperature_data[0]}")

            memory_frame = pd.DataFrame(record["process"]["memory_full_info"] for record in records_parsed)
            self.proc_mem_uss = memory_frame["uss"].max()
            self.proc_mem_pss = memory_frame["pss"].max()
            self.proc_mem_rss = memory_frame["rss"].max()
            self.proc_mem_vms = memory_frame["vms"].max()

            self.proc_ctx_switches_voluntary = first_last_difference["process"]["num_ctx_switches"]["voluntary"]
            self.proc_ctx_switches_involuntary = first_last_difference["process"]["num_ctx_switches"]["involuntary"]

            #     # Jetson-TK1 does not support these.
            # try:
            #     self.proc_io_read_count = first_last_difference["process"]["io_counters"]["read_count"]
            #     self.proc_io_read_bytes = first_last_difference["process"]["io_counters"]["read_bytes"]
            #     self.proc_io_write_count = first_last_difference["process"]["io_counters"]["write_count"]
            #     self.proc_io_write_bytes = first_last_difference["process"]["io_counters"]["write_bytes"]
            # except KeyError:
            #     logging.warning(f"Missing proc IO counters on endpoint {self}")

            interface_stats = first_last_difference["system"]["net_io_counters"][self.machine.ptp_interface]
            self.sys_net_ptp_iface_bytes_sent = interface_stats["bytes_sent"]
            self.sys_net_ptp_iface_packets_sent = interface_stats["packets_sent"]
            self.sys_net_ptp_iface_bytes_received = interface_stats["bytes_recv"]
            self.sys_net_ptp_iface_packets_received = interface_stats["packets_recv"]

            self.sys_net_ptp_iface_packets_total = (self.sys_net_ptp_iface_packets_received + self.sys_net_ptp_iface_packets_sent)
            self.sys_net_ptp_iface_bytes_total = (self.sys_net_ptp_iface_bytes_received + self.sys_net_ptp_iface_bytes_sent)

            self.save()


    def clear_analysis_data(self):
        # Remove existing data. Does not clear the associated profile data.
        self.sample_set.all().delete()


    def log(self, message: str, source: str):
        """Log to a logger with the name 'source'. Message will be intercepted by the log to database adapter and
        saved as a log record."""
        logging.getLogger(source).info(message)

    @property
    def benchmark(self) -> Benchmark:
        from ptp_perf.registry.benchmark_db import BenchmarkDB
        return BenchmarkDB.get(self.profile.benchmark_id)

    @property
    def machine(self) -> Machine:
        return config.machines.get(self.machine_id)

    @property
    def cluster(self) -> Cluster:
        return self.profile.cluster

    @property
    def storage_base_path(self) -> Path:
        return self.benchmark.storage_base_path.joinpath(self.profile.vendor.id).joinpath(str(self.id))

    @property
    def filename_base(self) -> str:
        return f"{self.machine_id}"

    def get_chart_timeseries_path(self, convergence_included: bool = False) -> Path:
        suffix = "" if not convergence_included else "-convergence"
        return self.storage_base_path.joinpath(f"{self.filename_base}{suffix}.pdf")

    def get_title(self, extra_info: str = None):
        return f"{self.benchmark.name} ({self.profile.vendor.name}" + (
            f", {extra_info})" if extra_info is not None else ")")

    def __str__(self):
        return f"{self.machine_id} (E{self.id}, {self.profile})"

    def get_effective_client_type(self) -> MachineClientType:
        return self.machine.get_effective_client_type(failover_active=self.benchmark.fault_failover)

    class Meta:
        app_label = 'app'

    def export_as_json(self) -> str:
        """Export this endpoint to a JSON representation"""
        return json.dumps(self.export_as_dict(), indent=4, cls=ModelJSONEncoder)

    def export_as_dict(self):
        endpoint_as_dict = model_to_dict(self)
        endpoint_as_dict["logrecord_set"] = list(self.logrecord_set.values())
        endpoint_as_dict["sample_set"] = list(self.sample_set.values())
        return endpoint_as_dict
