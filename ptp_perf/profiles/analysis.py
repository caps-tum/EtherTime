import logging
from dataclasses import dataclass
from datetime import timedelta, datetime
from typing import Optional

import numpy as np
import pandas as pd

from ptp_perf.profiles.data_container import COLUMN_CLOCK_DIFF, Timeseries


@dataclass
class DetectedClockStep:
    time: datetime
    magnitude: float

def detect_clock_step(clock_diff_series: pd.Series, max_permissible_clock_steps=1) -> DetectedClockStep:
    # First, detect the clock step (difference >= 1 second).
    first_difference = clock_diff_series.diff().abs()
    clock_steps = first_difference[first_difference >= 1]
    if max_permissible_clock_steps is not None and len(clock_steps) > max_permissible_clock_steps:
        raise RuntimeError(f"Found more than one clock step in timeseries profile: {clock_steps}")
    elif len(clock_steps) == 0:
        logging.warning(f"No clock step found in profile of length {len(clock_diff_series)}.")
        # Just set it close to the benchmark starting time.
        clock_step_time = first_difference.index.min() - timedelta(seconds=1)
        clock_step_magnitude = 0
    else:
        clock_step_time = clock_steps.index[0]
        clock_step_magnitude = clock_steps.values[0]
        # The clock step should occur in the first minute and has a magnitude of 1 minute,
        # thus should occur before timestamp 2 minutes.
        if not (50 <= clock_step_magnitude <= 70):
            logging.warning(f"The clock step was not of a magnitude close to 1 minute: {clock_step_magnitude}")

        min_timestamp = clock_diff_series.index.min()
        if clock_step_time - min_timestamp >= timedelta(minutes=2):
            logging.warning(f"The clock step was not within the first 2 minutes of runtime: {clock_steps}")
    return DetectedClockStep(time=clock_step_time, magnitude=clock_step_magnitude)


@dataclass
class DetectedClockConvergence:
    timestamp: datetime
    duration: timedelta
    converged: pd.Series

    @property
    def divergence_ratio(self) -> Optional[float]:
        """The amount of samples after the convergence time that were in diverged state."""
        cropped = self.converged[self.converged.index > self.timestamp]

        if len(cropped) == 0:
            logging.warning(f"No convergence data after convergence time of {self.timestamp}.")
            return None

        return len(cropped[cropped == 0]) / len(cropped)

    @property
    def divergence_counts(self):
        return (self.converged.diff() < 0).sum()


def detect_clock_convergence(series_with_convergence: pd.Series, minimum_convergence_time: timedelta) -> Optional[DetectedClockConvergence]:
    # Detect when the clock is synchronized and crop the convergence.
    # We say that the signal is converged when there are both negative and positive offsets within the window.
    window_centered = 10
    window_converged = 60
    rolling_data = series_with_convergence.rolling(window=window_centered, center=True)
    centered: pd.Series = (rolling_data.min() < 0) & (rolling_data.max() > 0)
    converged: pd.Series = centered.rolling(window=window_converged, center=True).median().apply(np.floor)
    # Fill the NA values that we have at the boundaries
    # Not optimal, this might also fill N/A values somewhere in the center.
    converged.ffill(inplace=True)
    converged.bfill(inplace=True)
    convergence_changes = converged[converged.diff() != 0]

    # Once we converge, we should stay converged.
    if not converged.any():
        logging.warning(f"Clock never converged.")
        return None
    if converged.isna().all():
        logging.warning(f"Profile too short, convergence test resulted in only N/A values.")
        return None

    # Initial convergence point
    # This is the first point where the converged value becomes 1.0
    convergence_timestamp = converged[converged == 1].index.min()
    min_total_timestamp = series_with_convergence.index.min()
    convergence_duration = convergence_timestamp - min_total_timestamp

    if convergence_duration < minimum_convergence_time:
        logging.warning(f"Convergence too fast: {convergence_duration}. Assuming 1 second.")
        convergence_timestamp = min_total_timestamp + minimum_convergence_time

    detected_convergence = DetectedClockConvergence(convergence_timestamp, convergence_timestamp - min_total_timestamp, converged)

    if detected_convergence.divergence_ratio is not None and detected_convergence.divergence_ratio > 0.1:
        logging.warning(f"Clock diverged {detected_convergence.divergence_counts}x after converging "
                        f"({detected_convergence.divergence_ratio * 100:.0f}% of samples in diverged state).")

    return detected_convergence
