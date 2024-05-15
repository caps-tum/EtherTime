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
    def ratio_converged_samples(self) -> Optional[float]:
        """The amount of samples after the convergence time that were in diverged state."""
        cropped = self.converged_after_clock_step

        if len(cropped) == 0:
            logging.warning(f"No convergence data after convergence time of {self.timestamp}.")
            return None

        return cropped.sum() / len(cropped)

    @property
    def num_converged_samples(self) -> Optional[int]:
        return len(self.converged_after_clock_step == 1)

    @property
    def converged_after_clock_step(self):
        return self.converged[self.converged.index > self.timestamp]


def detect_clock_convergence(series_with_convergence: pd.Series, minimum_convergence_time: timedelta) -> Optional[DetectedClockConvergence]:
    # Detect when the clock is synchronized and crop the convergence.

    # We say that the signal is converged when there are both negative and positive offsets within the window.
    # window_centered_interval = 10
    # We stabilize by majority voting of 3 10-second windows.
    # window_converged_interval = 10 * 3

    # This is number of samples, *not time*
    window_size = 15

    # rolling_data = series_with_convergence.rolling(window=window_centered_interval, center=True)
    # centered: pd.Series = (rolling_data.min() < 0) & (rolling_data.max() > 0)
    # converged: pd.Series = centered.rolling(window=window_converged_interval, center=True).mean() > 90

    # np.sign(data): This computes the sign of each number in the series (1 for positive, -1 for negative, 0 for zero).
    sign_changes_series = np.sign(series_with_convergence).diff().abs() / 2
    sign_changes_only = sign_changes_series[sign_changes_series > 0]
    rolling_sign_changes = sign_changes_series.astype(float).rolling(window=window_size).sum()

    # Converged is where we have at least 3 flips within {window_size} samples
    # We use this for calculating statistics
    assert minimum_convergence_time.total_seconds() == 10
    converged = rolling_sign_changes > 3

    # Fill the NA values that we have at the boundaries
    # Not optimal, this might also fill N/A values somewhere in the center.
    # converged.ffill(inplace=True)
    # converged.bfill(inplace=True)
    # New solution (safer): If we don't know, then its not converged.
    converged.fillna(0, inplace=True)

    # Initial convergence point
    # We allow the sign to flip 5 times during initial synchronization
    num_flips_during_convergence = 5
    if len(sign_changes_only) < num_flips_during_convergence:
        logging.warning(f"Clock never converged.")
        return None
    convergence_timestamp = (sign_changes_only == 1).index[num_flips_during_convergence]

    # if converged.isna().all():
    #     logging.warning(f"Profile too short, convergence test resulted in only N/A values.")
    #     return None

    convergence_duration = calculate_convergence_duration(convergence_timestamp, series_with_convergence)

    if convergence_duration < minimum_convergence_time:
        logging.warning(f"Convergence too fast: {convergence_duration}. Assuming {minimum_convergence_time} seconds.")
        # Set convergence to start of profile + minimum convergence time
        convergence_timestamp = series_with_convergence.index.min() + minimum_convergence_time
        convergence_duration = calculate_convergence_duration(convergence_timestamp, series_with_convergence)

    detected_convergence = DetectedClockConvergence(convergence_timestamp, convergence_duration, converged)

    ratio_converged_samples = detected_convergence.ratio_converged_samples
    if ratio_converged_samples is not None and ratio_converged_samples < 0.9:
        logging.warning(
            f"Clock stability low: ({ratio_converged_samples * 100:.0f}% of samples in converged state)."
        )

    return detected_convergence


def calculate_convergence_duration(convergence_timestamp: datetime, timeseries: pd.Series) -> timedelta:
    return convergence_timestamp - timeseries.index.min()
