import matplotlib.colors
import numpy as np
import seaborn
from django.test import TestCase
from matplotlib import pyplot as plt

from ptp_perf import config
from ptp_perf.charts.figure_container import FigureContainer, AxisContainer
from ptp_perf.charts.timeseries_element import ScatterElement
from ptp_perf.config import CLUSTER_RPI_SERV, CLUSTER_PI
from ptp_perf.models import BenchmarkSummary, PTPEndpoint, PTPProfile
from ptp_perf.models.data_transform import DataTransform
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.utilities.pandas_utilities import frame_column, foreign_frame_column
from ptp_perf.vendor.registry import VendorDB


class PathDelayChart(TestCase):

    def test_path_delay_variation(self):
        data = DataTransform(
            expansions=[PTPEndpoint.profile],
        ).run(
            PTPEndpoint.objects.filter(
                # Use data from all clusters
                # profile__cluster_id=CLUSTER_PI.id
                profile__cluster_id__in=config.ANALYZED_CLUSTER_IDS,
                profile__vendor_id__in=VendorDB.ANALYZED_VENDOR_IDS,
                profile__is_processed=True,
                profile__is_corrupted=False,
            ).select_related("profile").all()
        )
        print(data)
        data[frame_column(PTPEndpoint.clock_diff_median) + '_log'] = np.log10(data[frame_column(PTPEndpoint.clock_diff_median)])

        print(data)
        hue_norm = matplotlib.colors.LogNorm(vmin=1e-7, vmax=10e-3)
        color_map = 'coolwarm'
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
                            style_order=VendorDB.ANALYZED_VENDOR_IDS,
                            # color_map=seaborn.cubehelix_palette(gamma=1, rot=-.2, as_cmap=True),
                            color_map=seaborn.color_palette(color_map, as_cmap=True),
                            hue_norm=hue_norm,
                            edgecolor='.4',
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

        # handles, labels = figure.axes_containers[0].axis.get_legend_handles_labels()
        # figure.axes_containers[0].axis.legend(
        #     handles,
        #     # labels,
        #     # ["Clock Diff", "1μs", "10μs", "100μs", "1ms", "Vendor", "PTPd", "LinuxPTP", "SPTP", "Chrony"],
        #     ["Clock Diff", "1μs", "100μs", "10ms", "Vendor", "PTPd", "LinuxPTP", "SPTP", "Chrony"],
        #     loc="center left",
        #     bbox_to_anchor=(1, 0.5),
        # )

        # Color bar
        sm = plt.cm.ScalarMappable(cmap=color_map, norm=hue_norm)
        # sm.set_array([])  # Only needed for matplotlib < 3.1
        figure.figure.colorbar(sm, ax=figure.axes_containers[0].axis, label='Median Clock Offset', format=AxisContainer.get_time_formatter())

        # Add a custom legend for the style variable
        handles, labels = figure.axes_containers[0].axis.get_legend_handles_labels()
        style_labels = VendorDB.ANALYZED_VENDOR_IDS
        # Filter out hue handles and labels, only keep style
        style_handles = [handles[i] for i, label in enumerate(labels) if label in style_labels]
        plt.legend(
            title='Vendors',
            handles=style_handles,
            labels=[VendorDB.get(vendor_id).name for vendor_id in style_labels],
            loc='best'
        )

        # cbar = plt.colorbar()
        # cbar.set_ticks([1e-9, 1e-6, 1e-3])  # Define your desired tick positions
        # cbar.set_ticklabels(['1ns', '1us', '1ms'])  # Optional: Define labels for the ticks

        figure.save_default_locations("clock_diff_by_path_delay", BenchmarkDB.BASE)
