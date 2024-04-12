from dataclasses import dataclass

import seaborn

from ptp_perf.charts.figure_container import DataElement, AxisContainer


@dataclass
class ComparisonBarElement(DataElement):

    def plot(self, axis_container: AxisContainer):
        seaborn.barplot(
            self.data,
            ax=axis_container.axis,
            x=self.column_x,
            y=self.column_y,
            hue=self.column_hue,
            palette=self.color_map,
            errorbar=('pi', 100),
            native_scale=True,
        )

@dataclass
class ComparisonLineElement(DataElement):

    def plot(self, axis_container: AxisContainer):
        seaborn.lineplot(
            self.data,
            ax=axis_container.axis,
            x=self.column_x,
            y=self.column_y,
            hue=self.column_hue,
            palette=self.color_map,
            marker='o',
            errorbar=('pi', 100),
        )
