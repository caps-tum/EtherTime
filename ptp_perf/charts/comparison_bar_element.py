from dataclasses import dataclass
from datetime import timedelta
from typing import Union, Literal, List, Optional, Tuple

import numpy as np
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
    native_scale: bool = True

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
            native_scale=self.native_scale,
            dodge=self.dodge,
            order=self.order,
            hue_order=self.hue_order,
        )

@dataclass
class ComparisonLineElement(DataElement):
    marker: str = 'o'
    x_coord_aggregate: Union[float, timedelta] = None
    x_coord_aggregate_exclude_column: str = None
    x_coord_aggregate_shift_x_extremities: Union[float, timedelta] = None
    estimator: str = 'median'
    errorbar: Tuple = ('pi', 100)

    def plot(self, axis_container: AxisContainer):
        if self.x_coord_aggregate is not None:
            self.data = self.data.copy()

            # If we need to, shift the first and last values slightly so they are explicitly displayed.
            target_dtype = self.data[self.column_x].dtype
            epsilon = np.zeros(len(self.data), dtype=target_dtype)
            if self.x_coord_aggregate_shift_x_extremities:
                shift = np.array(self.x_coord_aggregate_shift_x_extremities, dtype=target_dtype)
                epsilon[self.data[self.column_x].argmin()] -= shift
                epsilon[self.data[self.column_x].argmax()] += shift

            # This rounds to the nearest multiple of the x value
            shifts = np.round(self.data[self.column_x] / self.x_coord_aggregate) * self.x_coord_aggregate - self.data[self.column_x]
            if self.x_coord_aggregate_exclude_column is not None:
                shifts *= ~self.data[self.x_coord_aggregate_exclude_column]
            self.data[self.column_x] += shifts + epsilon

        seaborn.lineplot(
            self.data,
            ax=axis_container.axis,
            x=self.column_x,
            y=self.column_y,
            hue=self.column_hue,
            palette=self.color_map,
            marker=self.marker,
            estimator=self.estimator,
            errorbar=self.errorbar,
        )
