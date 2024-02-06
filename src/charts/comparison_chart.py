from datetime import timedelta
from typing import List, Union, Callable, Tuple

import pandas as pd
import seaborn
from matplotlib import pyplot as plt

from charts.chart_container import ChartContainer
from profiles.base_profile import BaseProfile
from profiles.data_container import Timeseries, SummaryStatistics, ConvergenceStatistics
from utilities import units


class ComparisonChart(ChartContainer):
    axes: plt.Axes
    profiles: List[BaseProfile]

    def __init__(self, title: str, profiles: List[BaseProfile], y_axis_decorate: bool = True):
        self.figure, self.axes = plt.subplots(
            nrows=1, ncols=1, figsize=(10, 7),
        )

        self.profiles = profiles
        self.plot_decorate_title(self.axes, title)

        if y_axis_decorate:
            self.plot_decorate_yaxis(self.axes, True)

    def plot_statistic(self, profile_callback: Callable[[BaseProfile], Tuple[float, float]]):
        data_points = [profile_callback(profile) for profile in self.profiles]
        data = pd.DataFrame(data_points, columns=["x", "y"])

        seaborn.scatterplot(
            ax=self.axes,
            x=data['x'],
            y=data['y']
        )
