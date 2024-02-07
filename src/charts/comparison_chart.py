from dataclasses import dataclass
from typing import List, Callable, Optional, Any

import pandas as pd
import seaborn
from matplotlib import pyplot as plt

from charts.chart_container import ChartContainer
from profiles.base_profile import BaseProfile


@dataclass
class ComparisonDataPoint:
    x: float
    y: float
    hue: Optional[Any]

class ComparisonChart(ChartContainer):
    axes: List[List[plt.Axes]]
    current_axes: plt.Axes
    profiles: List[BaseProfile]

    def __init__(self, title: str, profiles: List[BaseProfile], y_axis_decorate: bool = True, nrows=1, ncols=1):
        self.figure, self.axes = plt.subplots(
            nrows=nrows, ncols=ncols, figsize=(10, 7),
            squeeze=False,
            sharex="col", sharey="row",
        )
        self.current_axes = self.axes[0][0]

        self.profiles = profiles
        self.plot_decorate_title(self.current_axes, title)

        if y_axis_decorate:
            for axes_row in self.axes:
                self.plot_decorate_yaxis(axes_row[0], True)

    def plot_statistic(self, profile_callback: Callable[[BaseProfile], ComparisonDataPoint], x_axis_label: str, hue_name: str = None):
        data_points = [profile_callback(profile).__dict__ for profile in self.profiles]
        data = pd.DataFrame(data_points)

        seaborn.lineplot(
            ax=self.current_axes,
            x=data['x'],
            y=data['y'],
            hue=data['hue'].rename(hue_name),
            marker='o',
        )

        self.current_axes.set_xlabel(x_axis_label)

    def set_current_axes(self, row: int, col: int):
        self.current_axes = self.axes[row][col]
