import matplotlib.colors
import numpy as np
import seaborn
from django.test import TestCase
from matplotlib import pyplot as plt

from ptp_perf.charts.figure_container import FigureContainer, AxisContainer
from ptp_perf.charts.timeseries_element import ScatterElement
from ptp_perf.config import CLUSTER_RPI_SERV, CLUSTER_PI
from ptp_perf.models import BenchmarkSummary, PTPEndpoint, PTPProfile
from ptp_perf.models.data_transform import DataTransform
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.utilities.pandas_utilities import frame_column, foreign_frame_column


class PathDelayChart(TestCase):

    def test_path_delay_variation(self):
        data = DataTransform(
            expansions=[PTPEndpoint.profile],
        ).run(
            PTPEndpoint.objects.filter(
                # Use data from all clusters
                # profile__cluster_id=CLUSTER_PI.id
            ).select_related("profile").all()
        )
        data[frame_column(PTPEndpoint.clock_diff_median) + '_log'] = np.log10(data[frame_column(PTPEndpoint.clock_diff_median)])

        print(data)
        figure = FigureContainer(
            axes_containers=[
                AxisContainer(
                    data_elements=[
                        ScatterElement(
                            data=data,
                            column_x=frame_column(PTPEndpoint.path_delay_median),
                            column_y=frame_column(PTPEndpoint.path_delay_std),
                            column_hue=frame_column(PTPEndpoint.clock_diff_median),
                            column_style=foreign_frame_column(PTPEndpoint.profile, PTPProfile.vendor_id),
                            # color_map=seaborn.cubehelix_palette(gamma=1, rot=-.2, as_cmap=True),
                            color_map=seaborn.color_palette('viridis', as_cmap=True),
                            hue_norm=matplotlib.colors.LogNorm(vmin=1e-6, vmax=2.5e-3,),
                        )
                    ],
                    ylog=True,
                    yticklabels_format_time=True,
                    ylabel='Path Delay Std.',
                    xlog=True,
                    xticklabels_format_time=True,
                    xlabel='Path Delay',
                    legend=True,
                    title='Clock Difference for Path Delay and Path Delay Variation'
                )
            ],
            tight_layout=True,
            size=(6, 3.25),
        )
        figure.plot()

        handles, labels = figure.axes_containers[0].axis.get_legend_handles_labels()
        figure.axes_containers[0].axis.legend(
            handles,
            # labels,
            # ["Clock Diff", "1μs", "10μs", "100μs", "1ms", "Vendor", "PTPd", "LinuxPTP", "SPTP", "Chrony"],
            ["Clock Diff", "1μs", "100μs", "10ms", "Vendor", "PTPd", "LinuxPTP", "SPTP", "Chrony"],
            loc="center left",
            bbox_to_anchor=(1, 0.5),
        )

        # cbar = plt.colorbar()
        # cbar.set_ticks([1e-9, 1e-6, 1e-3])  # Define your desired tick positions
        # cbar.set_ticklabels(['1ns', '1us', '1ms'])  # Optional: Define labels for the ticks

        figure.save_default_locations("clock_diff_by_path_delay", BenchmarkDB.BASE)
