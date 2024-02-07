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

    def plot_statistic(self, profile_callback: Callable[[BaseProfile], ComparisonDataPoint], x_axis_label: str, hue_name: str = None):
        data_points = [profile_callback(profile).__dict__ for profile in self.profiles]
        data = pd.DataFrame(data_points)

        seaborn.lineplot(
            ax=self.axes,
            x=data['x'],
            y=data['y'],
            hue=data['hue'].rename(hue_name),
            marker='o',
        )

        self.axes.set_xlabel(x_axis_label)
