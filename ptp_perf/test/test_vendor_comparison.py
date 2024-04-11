from unittest import TestCase

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn

from ptp_perf import config
from ptp_perf.charts.chart_container import ChartContainer
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
                    resampled_data = data.droplevel('endpoint_id').abs().resample('60s').apply(
                        lambda group: group.median() if len(group) >= 30 else np.nan
                    ).dropna()

                    print('Resampled', vendor.name, resampled_data.min(), resampled_data.median(), resampled_data.max())

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

            plot = seaborn.barplot(
                frame,
                x='X',
                hue='Vendor',
                y='Value',
                errorbar=('pi', 100),
                native_scale=True,
                legend=False,
            )
            plot.set_xticks(list(frame['X']) + [1.5, 6.5])
            plot.set_xticklabels(list(frame['Label']) + ["\nRaspberry-Pi 4", "\nRaspberry-Pi 5"])

            chart = ChartContainer(figure=plot.get_figure())
            chart.plot_decorate_yaxis(plot, 'Clock Offset')
            chart.plot_decorate_title(plot, "Baseline Performance by Vendor and Cluster")

            chart.save(MEASUREMENTS_DIR.joinpath(benchmark.id).joinpath("vendor_comparison.png"))

                #
                # comparison_chart = ComparisonChart(
                #     title=f"Reproducibility ({benchmark.name})",
                #     profiles=endpoints,
                #     x_axis_label="Profile",
                #     use_bar=True,
                #     include_p99=False, include_p99_separate_axis=False,
                #     include_profile_confidence_intervals=True,
                #     include_annotate_range=True,
                #     ylimit_top=0.0001, ylimit_top_use_always=True,
                #     legend=False,
                # )
                # comparison_chart.plot_median_clock_diff_and_path_delay(
                #     x_axis_values=lambda endpoint: endpoints.index(endpoint),
                # )
                #
                # comparison_chart.save(benchmark.storage_base_path.joinpath(f"key_metric_variance.svg"))
                # comparison_chart.save(benchmark.storage_base_path.joinpath(f"key_metric_variance.pdf"))
