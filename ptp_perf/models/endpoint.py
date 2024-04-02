import logging
import re
import typing
from datetime import timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
from django.db import models
from django.db.models import CASCADE

from ptp_perf import config
from ptp_perf.machine import Machine
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.models.profile import PTPProfile
from ptp_perf.profiles.analysis import detect_clock_step, detect_clock_convergence
from ptp_perf.profiles.benchmark import Benchmark
from ptp_perf.profiles.data_container import Timeseries, ConvergenceStatistics
from ptp_perf.utilities import units

if typing.TYPE_CHECKING:
    from ptp_perf.models.sample import Sample


class PTPEndpoint(models.Model):
    id = models.AutoField(primary_key=True)

    profile: PTPProfile = models.ForeignKey(PTPProfile, on_delete=CASCADE)
    machine_id = models.CharField(max_length=255)
    restart_count = models.IntegerField(default=0)

    endpoint_type = models.CharField(choices=EndpointType, max_length=32, default=EndpointType.UNKNOWN)

    # Summary statistics
    clock_diff_median = models.FloatField(null=True)
    clock_diff_p99 = models.FloatField(null=True)
    path_delay_median = models.FloatField(null=True)

    # Convergence statistics
    convergence_timestamp = models.DateTimeField(null=True)
    convergence_duration = models.DurationField(null=True)
    convergence_max_offset = models.FloatField(null=True)
    convergence_rate = models.FloatField(null=True)

    # Clock step
    clock_step_timestamp = models.DateTimeField(null=True)
    clock_step_magnitude = models.FloatField(null=True)

    def load_samples_to_series(self, sample_type: "Sample.SampleType", converged_only: bool = True,
                               remove_clock_step: bool = True, normalize_time: bool = False) -> Optional[pd.Series]:
        from ptp_perf.models import Sample
        sample_set = self.sample_set.filter(sample_type=sample_type)

        if converged_only:
            if self.convergence_timestamp is None:
                raise RuntimeError(f"Requested converged data but no convergence time is present: {self}.")
            sample_set = sample_set.filter(timestamp__gte=self.convergence_timestamp)

        if remove_clock_step:
            if self.clock_step_timestamp is None:
                raise RuntimeError("Requested clock step exclusion but no clock step timestamp is present.")
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

        if normalize_time:
            series.index -= self.convergence_timestamp

        return series

    def process_timeseries_data(self):
        from ptp_perf.models.sample import Sample

        entire_series = self.load_samples_to_series(Sample.SampleType.CLOCK_DIFF, converged_only=False,
                                                    remove_clock_step=False)
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

        if detected_clock_convergence is not None:

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
            self.clock_diff_median = converged_series.median()
            self.clock_diff_p99 = converged_series.quantile(0.99)
            path_delay_values = self.load_samples_to_series(Sample.SampleType.PATH_DELAY, converged_only=True)
            self.path_delay_median = path_delay_values.median()

        else:
            # This profile is probably corrupt.
            self.profile.is_corrupted = True
            self.profile.save()
            logging.warning("Profile marked as corrupt.")

        self.save()
        return self

    def create_timeseries_charts(self, force_regeneration: bool = False):
        from ptp_perf.charts.timeseries_chart import TimeseriesChart
        from ptp_perf.models.sample import Sample

        # We create multiple charts:
        # one only showing the filtered data and one showing the entire convergence trajectory
        if self.convergence_timestamp is not None:
            clock_diff = self.load_samples_to_series(Sample.SampleType.CLOCK_DIFF, normalize_time=True)
            path_delay = self.load_samples_to_series(Sample.SampleType.PATH_DELAY, normalize_time=True)

            output_path = self.get_chart_timeseries_path()
            # if self.check_dependent_file_needs_update(output_path) or force_regeneration:
            chart = TimeseriesChart(
                title=self.get_title(),
                summary_statistics=None,
                # ylimit_top = 1,
                # ylimit_bottom = 0,
                ylog=True
            )
            chart.add_path_delay(path_delay)
            chart.add_clock_difference(clock_diff)
            chart.save(output_path, make_parents=True)

        if self.clock_step_timestamp is not None:
            clock_diff = self.load_samples_to_series(Sample.SampleType.CLOCK_DIFF, converged_only=False,
                                                     normalize_time=True)
            path_delay = self.load_samples_to_series(Sample.SampleType.PATH_DELAY, converged_only=False,
                                                     normalize_time=True)
            output_path = self.get_chart_timeseries_path(convergence_included=True)
            # if self.check_dependent_file_needs_update(output_path) or force_regeneration:
            chart_convergence = TimeseriesChart(
                title=self.get_title("with Convergence"),
                summary_statistics=None,
            )
            chart_convergence.add_path_delay(path_delay)
            chart_convergence.add_clock_difference(clock_diff)
            if self.convergence_duration is not None:
                chart_convergence.add_boundary(
                    chart_convergence.axes[0], self.convergence_duration
                )
            chart_convergence.save(output_path, make_parents=True)

    def process_fault_data(self):
        from ptp_perf.models import LogRecord, Sample
        records = LogRecord.objects.filter(source="fault-generator", endpoint__profile=self.profile).all()
        parsed_faults = 0
        for record in records:
            match = re.search(
                f"Scheduled (?P<type>\S+) fault (?P<status>imminent|resolved) on {self.machine_id}.",
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
    def storage_base_path(self) -> Path:
        return self.benchmark.storage_base_path.joinpath(self.profile.vendor.id).joinpath(str(self.id))

    @property
    def filename_base(self) -> str:
        return f"{self.machine_id}"

    def get_chart_timeseries_path(self, convergence_included: bool = False) -> Path:
        suffix = "" if not convergence_included else "-convergence"
        return self.storage_base_path.joinpath(f"{self.filename_base}{suffix}.png")

    def get_title(self, extra_info: str = None):
        return f"{self.benchmark.name} ({self.profile.vendor.name}" + (
            f", {extra_info})" if extra_info is not None else ")")

    def __str__(self):
        return f"{self.machine_id} (#{self.id}, {self.profile})"


    class Meta:
        app_label = 'app'
        db_table = "ptp_perf_ptpendpoint"
