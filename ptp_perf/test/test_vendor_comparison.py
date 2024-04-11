from unittest import TestCase

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn

from ptp_perf import config
from ptp_perf.charts.chart_container import ChartContainer
from ptp_perf.charts.comparison_bar_element import ComparisonBarElement
from ptp_perf.charts.figure_container import FigureContainer, AxisContainer
from ptp_perf.constants import MEASUREMENTS_DIR
from ptp_perf.models import Sample
from ptp_perf.models.endpoint_type import EndpointType
from ptp_perf.models.exceptions import NoDataError
from ptp_perf.models.sample_query import SampleQuery
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.vendor.registry import VendorDB


class VendorComparisonCharts(TestCase):

    def test_chart(self):

        for benchmark in [BenchmarkDB.BASE]:
            output_data = []
            vendors = VendorDB.ANALYZED_VENDORS
            for vendor_index, vendor in enumerate(vendors):

                for cluster_index, cluster in enumerate(config.clusters.values()):
                    try:
                        data_query = SampleQuery(
                            benchmark=benchmark,
                            vendor=vendor,
                            cluster=cluster,
                            endpoint_type=EndpointType.PRIMARY_SLAVE,
                            normalize_time=False, timestamp_merge_append=False
                        )
                        data = data_query.run(Sample.SampleType.CLOCK_DIFF)
                    except NoDataError:
                        continue

                    # data = data.resample('1m').
                    # resampled_data = data.droplevel('endpoint_id').abs().resample('60s').apply(
                    #     lambda group: group.median() if len(group) >= 30 else np.nan
                    # ).dropna()
                    #
                    # print('Resampled', vendor.name, resampled_data.min(), resampled_data.median(), resampled_data.max())

                    unmodified_data = data.droplevel('endpoint_id').abs()
                    quantiles = unmodified_data.quantile([0.05, 0.5, 0.95])
                    print('Unmodified', vendor.name, *quantiles)

                    # output_data.append({
                    #     'Vendor': vendor.name,
                    #     'Lower': quantiles[0],
                    #     'Median': quantiles[1],
                    #     'Upper': quantiles[2],
                    # })

                    for quantile in quantiles:
                        output_data.append({
                            'Label': f"{vendor.name}",
                            'X': (len(vendors) + 1) * cluster_index + vendor_index,
                            'Cluster': cluster.name,
                            'Vendor': vendor.name,
                            'Value': quantile,
                        })

            frame = pd.DataFrame(output_data)
            frame.sort_values('X', inplace=True)

            print(frame)

            # seaborn.set_style("whitegrid")

            chart = FigureContainer(
                [AxisContainer(
                    [ComparisonBarElement(
                        data=frame,
                        column_x='X',
                        column_y='Value',
                        column_hue='Vendor'
                    )],
                    title="Baseline Performance by Vendor and Cluster",
                    xticks=list(frame['X']) + [1.5, 6.5],
                    xticklabels=list(frame['Label']) + ["\nRaspberry-Pi 4", "\nRaspberry-Pi 5"],
                )],
            )
            chart.plot()

            chart.save(MEASUREMENTS_DIR.joinpath(benchmark.id).joinpath("vendor_comparison.svg"))
            chart.save(MEASUREMENTS_DIR.joinpath(benchmark.id).joinpath("vendor_comparison.pdf"))
