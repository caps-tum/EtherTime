import json
import logging
import re
import typing
from datetime import timedelta
from enum import StrEnum
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
from django.db import models
from django.db.models import CASCADE

from ptp_perf import config
from ptp_perf.machine import Machine, Cluster, MachineClientType
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.models.exceptions import NoDataError
from ptp_perf.models.profile import PTPProfile
from ptp_perf.profiles.analysis import detect_clock_step, detect_clock_convergence
from ptp_perf.profiles.benchmark import Benchmark
from ptp_perf.profiles.data_container import Timeseries, ConvergenceStatistics
from ptp_perf.utilities import units, psutil_utilities

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


class PTPEndpoint(models.Model):
    id = models.AutoField(primary_key=True)

    profile: PTPProfile = models.ForeignKey(PTPProfile, on_delete=CASCADE)
    machine_id = models.CharField(max_length=255)
    restart_count = models.IntegerField(default=0)

    endpoint_type = models.CharField(choices=EndpointType, max_length=32, default=EndpointType.UNKNOWN)

    # Summary statistics
    clock_diff_median = models.FloatField(null=True)
    clock_diff_p05 = models.FloatField(null=True)
    clock_diff_p95 = models.FloatField(null=True)
    path_delay_median = models.FloatField(null=True)
    path_delay_p05 = models.FloatField(null=True)
    path_delay_p95 = models.FloatField(null=True)
    path_delay_std = models.FloatField(null=True)

    # Convergence statistics
    convergence_timestamp = models.DateTimeField(null=True)
    convergence_duration = models.DurationField(null=True)
    convergence_max_offset = models.FloatField(null=True)
    convergence_rate = models.FloatField(null=True)

    # Clock step
    clock_step_timestamp = models.DateTimeField(null=True)
    clock_step_magnitude = models.FloatField(null=True)

    # Fault Data
    fault_clock_diff_pre_median = models.FloatField(null=True)
    fault_clock_diff_pre_p05 = models.FloatField(null=True)
    fault_clock_diff_pre_p95 = models.FloatField(null=True)
    fault_path_delay_pre_median = models.FloatField(null=True)
    fault_path_delay_pre_p05 = models.FloatField(null=True)
    fault_path_delay_pre_p95 = models.FloatField(null=True)

    fault_clock_diff_post_median = models.FloatField(null=True)
    fault_clock_diff_post_p05 = models.FloatField(null=True)
    fault_clock_diff_post_p95 = models.FloatField(null=True)
    fault_path_delay_post_median = models.FloatField(null=True)
    fault_path_delay_post_p05 = models.FloatField(null=True)
    fault_path_delay_post_p95 = models.FloatField(null=True)

    # Fault Summaries
    fault_actual_duration = models.DurationField(null=True)
    fault_ratio_clock_diff_median = models.FloatField(null=True)
    fault_ratio_clock_diff_p95 = models.FloatField(null=True)

    fault_clock_diff_post_max = models.FloatField(null=True)
    fault_ratio_clock_diff_post_max_pre_median = models.FloatField(null=True)

    # Resource consumption data
    proc_cpu_percent = models.FloatField(null=True)
    proc_cpu_percent_system = models.FloatField(null=True)
    proc_cpu_percent_user = models.FloatField(null=True)
    proc_mem_rss = models.FloatField(null=True)
    proc_mem_vms = models.FloatField(null=True)
    proc_io_write_count = models.FloatField(null=True)
    proc_io_write_bytes = models.FloatField(null=True)
    proc_io_read_count = models.FloatField(null=True)
    proc_io_read_bytes = models.FloatField(null=True)
    proc_ctx_switches_involuntary = models.FloatField(null=True)
    proc_ctx_switches_voluntary = models.FloatField(null=True)

    sys_net_ptp_iface_bytes_sent = models.FloatField(null=True)
    sys_net_ptp_iface_packets_sent = models.FloatField(null=True)
    sys_net_ptp_iface_bytes_received = models.FloatField(null=True)
    sys_net_ptp_iface_packets_received = models.FloatField(null=True)

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
            reference_points = {
                TimeNormalizationStrategy.PROFILE_START: self.profile.start_time,
                TimeNormalizationStrategy.CLOCK_STEP: self.clock_step_timestamp,
                TimeNormalizationStrategy.CONVERGENCE: self.convergence_timestamp,
            }
            series.index -= reference_points[normalize_time]

        return series

    def process_timeseries_data(self):
        from ptp_perf.models.sample import Sample
        from ptp_perf.models.log_record import LogRecord

        entire_series = self.load_samples_to_series(Sample.SampleType.CLOCK_DIFF, converged_only=False,
                                                    remove_clock_step=False, normalize_time=TimeNormalizationStrategy.NONE)
        if entire_series is None:
            return

        timestamps = entire_series.index
        if not isinstance(timestamps.dtype, pd.DatetimeTZDtype):
            raise RuntimeError(f"Received a time series the is not a datetime64+tz (type: {timestamps.dtype}).")

        # Basic sanity checks, no duplicate timestamps
        if not timestamps.is_unique:
            value_counts = timestamps.value_counts()
            duplicate_timestamps = value_counts[value_counts != 1]
            raise RuntimeError(f"Timestamps not unique:\n{duplicate_timestamps}")
        if not timestamps.is_monotonic_increasing:
            time_index_diff = entire_series.index.diff()
            raise RuntimeError(
                f"Timestamps not monotonically increasing:\n{time_index_diff[time_index_diff < timedelta(seconds=0)]}"
            )

        # We don't normalize time automatically anymore.
        # Normalize time: Move the origin to the epoch
        # timestamps = timestamps - timestamps.min()

        Timeseries._validate_series(entire_series, maximum_allowable_time_jump=timedelta(minutes=1, seconds=10))

        # Do some data post-processing to improve quality.

        # Step 1: Remove the first big clock step.

        # Remove any beginning zero values (no clock_difference information yet) from start
        # (first non-zero value makes cumulative sum >= 0)
        crop_condition = (entire_series != 0).cumsum()
        frame_no_leading_zeros = entire_series[crop_condition != 0]

        detected_clock_step = detect_clock_step(frame_no_leading_zeros, self.benchmark.analyze_limit_permissible_clock_steps)
        self.clock_step_timestamp = detected_clock_step.time
        self.clock_step_magnitude = detected_clock_step.magnitude

        # Now crop after clock step
        logging.debug(f"Clock step at {detected_clock_step.time}: {detected_clock_step.magnitude}")
        frame_no_clock_step = frame_no_leading_zeros[frame_no_leading_zeros.index > detected_clock_step.time]

        Timeseries._validate_series(frame_no_clock_step)

        minimum_convergence_time = timedelta(seconds=1)
        detected_clock_convergence = detect_clock_convergence(frame_no_clock_step, minimum_convergence_time)

        if detected_clock_convergence is None:
            raise ProfileCorruptError("No clock convergence detected.")

        remaining_benchmark_time = frame_no_clock_step.index.max() - detected_clock_convergence.timestamp
        if remaining_benchmark_time < self.benchmark.duration * 0.75:
            logging.warning(
                f"Cropping of convergence zone resulted in a low remaining benchmark data time of {remaining_benchmark_time}")

        # Create some convergence statistics
        convergence_series = frame_no_clock_step[frame_no_clock_step.index <= detected_clock_convergence.timestamp]
        convergence_statistics = ConvergenceStatistics.from_convergence_series(detected_clock_convergence,
                                                                               convergence_series)
        self.convergence_timestamp = detected_clock_convergence.timestamp
        self.convergence_duration = detected_clock_convergence.duration
        self.convergence_rate = convergence_statistics.convergence_rate
        self.convergence_max_offset = convergence_statistics.convergence_max_offset

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
                raise NotImplementedError("Cannot support multiple faults in one profile at the moment.")
            fault_start = faults.filter(value=1).get()
            fault_end = faults.filter(value=0).get()
            if fault_start.timestamp <= self.convergence_timestamp:
                raise ProfileCorruptError("Clock did not converge before the first fault.")
            if fault_start.timestamp >= fault_end.timestamp:
                raise ProfileCorruptError("Fault ended before it started?")
            if fault_end.timestamp > max(frame_no_clock_step.index):
                # TODO: Investigate fault corruption
                raise ProfileCorruptError(
                    f"Fault occurred after last sample timestamp? "
                    f"Data interval: [{min(frame_no_clock_step.index)}, {max(frame_no_clock_step.index)}], "
                    f"Fault interval: [{fault_start.timestamp}, {fault_end.timestamp}]"
                )

            pre_fault_series = abs_clock_diff[abs_clock_diff.index <= fault_start.timestamp]
            self.fault_clock_diff_pre_median, self.fault_clock_diff_pre_p05, self.fault_clock_diff_pre_p95 = (
                self.calculate_quantiles(pre_fault_series)
            )
            pre_fault_path_delay = path_delay_values[path_delay_values.index <= fault_start.timestamp]
            self.fault_path_delay_pre_median, self.fault_path_delay_pre_p05, self.fault_path_delay_pre_p95 = (
                self.calculate_quantiles(pre_fault_path_delay)
            )

            post_fault_series = abs_clock_diff[abs_clock_diff.index >= fault_end.timestamp]
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

        except (NoDataError, Sample.DoesNotExist):
            if self.benchmark.fault_location is not None:
                raise ProfileCorruptError(f"Could not find fault for profile {self.profile} on benchmark {self.benchmark}")

        self.save()
        return self

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

    def create_timeseries_chart_convergence(self) -> "TimeseriesChart":
        from ptp_perf.charts.timeseries_chart import TimeseriesChart
        from ptp_perf.models.sample import Sample
        clock_diff = self.load_samples_to_series(
            Sample.SampleType.CLOCK_DIFF,
            converged_only=False, remove_clock_step_force=False, normalize_time=TimeNormalizationStrategy.CLOCK_STEP,
        )
        path_delay = self.load_samples_to_series(
            Sample.SampleType.PATH_DELAY,
            converged_only=False, remove_clock_step_force=False, normalize_time=TimeNormalizationStrategy.CLOCK_STEP,
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
                chart_convergence.axes[0], self.convergence_duration
            )
        return chart_convergence

    def process_fault_data(self):
        from ptp_perf.models import LogRecord, Sample
        records = LogRecord.objects.filter(source="fault-generator", endpoint__profile=self.profile).all()
        parsed_faults = 0
        for record in records:
            # We import faults either directly on the current endpoint.
            # If we are the orchestrator, then we get faults from the switch.
            location = self.machine_id if self.machine_id != 'orchestrator' else 'switch'
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
            logging.info(f"{self} parsed {parsed_faults} fault status records.")
        return parsed_faults


    def process_system_metrics_data(self):
        from ptp_perf.models import LogRecord
        from ptp_perf.adapters.resource_monitor import ResourceMonitor
        records = LogRecord.objects.filter(
            source=ResourceMonitor.log_source, endpoint__profile=self.profile
        ).exclude(
            message__contains='"process": {}'
        ).order_by('id').all()

        # Check if any data available
        if len(records) != 0:

            # Difference data: data based on counter can be subtracted and converted into a rate where applicable.
            first_record: LogRecord = records.first()
            last_record: LogRecord = records.last()

            first_last_difference = psutil_utilities.hierarchical_apply(
                json.loads(last_record.message), json.loads(first_record.message),
                lambda x, y: x - y,
            )
            measurement_timedelta = last_record.timestamp - first_record.timestamp
            self.proc_cpu_percent_system = first_last_difference["process"]["cpu_times"]["system"] / measurement_timedelta.total_seconds()
            self.proc_cpu_percent_user = first_last_difference["process"]["cpu_times"]["user"] / measurement_timedelta.total_seconds()
            self.proc_cpu_percent = self.proc_cpu_percent_system + self.proc_cpu_percent_user

            memory_frame = pd.DataFrame(json.loads(record.message)["process"]["memory_full_info"] for record in records)
            self.proc_mem_vms = memory_frame["vms"].max()
            self.proc_mem_rss = memory_frame["rss"].max()

            self.proc_ctx_switches_voluntary = first_last_difference["process"]["num_ctx_switches"]["voluntary"]
            self.proc_ctx_switches_involuntary = first_last_difference["process"]["num_ctx_switches"]["involuntary"]

            self.proc_io_read_count = first_last_difference["process"]["io_counters"]["read_count"]
            self.proc_io_read_bytes = first_last_difference["process"]["io_counters"]["read_bytes"]
            self.proc_io_write_count = first_last_difference["process"]["io_counters"]["write_count"]
            self.proc_io_write_bytes = first_last_difference["process"]["io_counters"]["write_bytes"]

            interface_stats = first_last_difference["system"]["net_io_counters"]["eth0"]
            self.sys_net_ptp_iface_bytes_sent = interface_stats["bytes_sent"]
            self.sys_net_ptp_iface_packets_sent = interface_stats["packets_sent"]
            self.sys_net_ptp_iface_bytes_received = interface_stats["bytes_recv"]
            self.sys_net_ptp_iface_packets_received = interface_stats["packets_recv"]


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
        return f"{self.machine_id} (#{self.id}, {self.profile})"

    def get_effective_client_type(self) -> MachineClientType:
        return self.machine.get_effective_client_type(failover_active=self.benchmark.fault_failover)

    class Meta:
        app_label = 'app'
