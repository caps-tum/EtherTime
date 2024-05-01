from dataclasses import dataclass
from typing import Union, Literal, List, Optional

import seaborn

from ptp_perf.charts.figure_container import DataElement, AxisContainer
from ptp_perf.vendor.registry import VendorDB


@dataclass
class ComparisonBarElement(DataElement):
    dodge: Union[Literal["auto"], bool] = "auto"
    order_vendors: bool = False
    order: Optional[List[str]] = None
    hue_order_vendors: bool = False
    hue_order: Optional[List[str]] = None

    def plot(self, axis_container: AxisContainer):

        if self.order_vendors:
            self.order = [vendor.id for vendor in VendorDB.ANALYZED_VENDORS]
        if self.hue_order_vendors:
            self.hue_order = [vendor.id for vendor in VendorDB.ANALYZED_VENDORS]

        seaborn.barplot(
            self.data,
            ax=axis_container.axis,
            x=self.column_x,
            y=self.column_y,
            hue=self.column_hue,
            palette=self.color_map,
            estimator='median',
            errorbar=('pi', 100),
            native_scale=True,
            dodge=self.dodge,
            order=self.order,
            hue_order=self.hue_order,
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
            estimator='median',
            errorbar=('pi', 100),
        )
