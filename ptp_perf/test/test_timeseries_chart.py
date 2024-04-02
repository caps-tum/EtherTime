from typing import List
from unittest import TestCase

from ptp_perf.utilities.django_utilities import bootstrap_django_environment
bootstrap_django_environment()

from ptp_perf import constants
from ptp_perf.models.profile_query import ProfileQuery
from ptp_perf.models.sample_query import SampleQuery
from ptp_perf.charts.distribution_comparison_chart import DistributionComparisonChart
from ptp_perf.charts.timeseries_chart_versus import TimeSeriesChartVersus
from ptp_perf.models import PTPProfile, Sample
from ptp_perf.registry.benchmark_db import BenchmarkDB
from ptp_perf.vendor.registry import VendorDB


class TestTimeseriesChart(TestCase):
    # def test_create(self):
    #     profile = PTPDTimeSeriesProfile.load_str(TEST_TIMESERIES_PROFILE)
    #     chart = TimeseriesChart()
    #     chart.create(profile)
    #     chart.save("test-series.png")

    def test_individual_charts(self):
        # profiles = ProfileDB().resolve_all(resolve.VALID_PROCESSED_PROFILE())
        # profiles += ProfileDB().resolve_all(resolve.CORRUPT_PROCESSED_PROFILE())
        # profiles += ProfileDB().resolve_all(resolve.AGGREGATED_PROFILE())
        profiles = ProfileQuery().run()

        for profile in profiles:
            print(f"Processing {profile}")
            for endpoint in profile.ptpendpoint_set.all():
                endpoint.create_timeseries_charts()


    def test_comparison(self):
        ptpd_profile = SampleQuery(
            benchmark=BenchmarkDB.BASE,
            vendor=VendorDB.PTPD,
        )
        linuxptp_profile = SampleQuery(
            benchmark=BenchmarkDB.BASE,
            vendor=VendorDB.LINUXPTP,
        )

        # TODO: Sample queries might be empty but they are not none
        # if ptpd_profile is None or linuxptp_profile is None:
        #     self.skipTest("Required profile not found")

        chart = TimeSeriesChartVersus(ptpd_profile, linuxptp_profile)
        chart.set_titles("PTPd", "LinuxPTP")
        chart.save(constants.CHARTS_DIR.joinpath("vendors").joinpath("ptpd-vs-linuxptp.png"), make_parents=True)

    def test_history(self):
        self.create_history_charts(BenchmarkDB.BASE)

    def create_history_charts(self, benchmark, y_log=False):
        for vendor in VendorDB.all():
            profiles = ProfileQuery(
                benchmark=benchmark,
                vendor=vendor
            ).run()


            if len(profiles) == 0:
                continue

            chart = DistributionComparisonChart(
                [SampleQuery(profile=profile) for profile in profiles],
                [f"#{index+1}: {profile.start_time.replace(second=0, microsecond=0)}" for index, profile in enumerate(profiles)],
                x_label="Profile Date",
            )
            if y_log:
                chart.axes[0].set_yscale('log')
                chart.axes[1].set_yscale('log')
            chart.axes[0].set_title(f"Profile History: {benchmark.name} using {vendor}")
            chart.save(constants.CHARTS_DIR.joinpath("history").joinpath(f"{benchmark.id}-history-{vendor}.png"),
                       make_parents=True)

    # def create_figure(self, profile: BaseProfile):
    #
        # seaborn.lineplot(
        #     frame,
        #     x="boxplot_x", y=PTPDTimeSeriesProfile.COLUMN_CLOCK_OFFSET,
        #     ax=axes[1]
        # )
        # seaborn.lineplot(
        #     frame,
        #     x=PTPDTimeSeriesProfile.COLUMN_TIMESTAMP, y='clock_offset_mean',
        #     ax=axes[1]
        # )
        # seaborn.lineplot(
        #     frame,
        #     x=PTPDTimeSeriesProfile.COLUMN_TIMESTAMP, y='clock_offset_mean_confidence_low',
        #     ax=axes[1]
        # )
        # seaborn.lineplot(
        #     frame,
        #     x=PTPDTimeSeriesProfile.COLUMN_TIMESTAMP, y='clock_offset_mean_confidence_high',
        #     ax=axes[1]
        # )

        # seaborn.lineplot(
        #     # x=frame[PTPDTimeSeriesProfile.COLUMN_TIMESTAMP],
        #     profile.rolling_clock_offset(frame, window_size=timedelta(seconds=180)).apply(
        #         lambda values: (values < 0).sum() / len(values)
        #     ),
        #     ax=axes[1]
        # )
        # seaborn.lineplot(
        #     # x=frame[PTPDTimeSeriesProfile.COLUMN_TIMESTAMP],
        #     profile.resampled_clock_offset(frame, window_size=timedelta(seconds=10)).std(),
        #     ax=axes[1][0]
        # )

        # axes[1].yaxis.set_data_interval(0, 1)

        # seaborn.violinplot(
        #     x=frame["boxplot_x"], y=frame[PTPDTimeSeriesProfile.COLUMN_CLOCK_OFFSET_ABS],
        #     ax=axes[1]
        # )

        # frame["differences"] = frame["clock_offset"].diff()
        # seaborn.lineplot(frame, x="timestamp", y="differences", ax=axes[1])
        # TimeseriesChart.decorate_plot(axes[1])

        # for ax_row in axes:
        #     ax_row[0].hlines(
        #         y=[ax_row[0].yaxis.get_view_interval()[0] + abs(ax_row[0].yaxis.get_view_interval()[0] * 0.1)] * len(frame),
        #         xmin=frame[PTPDTimeSeriesProfile.COLUMN_TIMESTAMP],
        #         xmax=frame[PTPDTimeSeriesProfile.COLUMN_TIMESTAMP].shift(),
        #         colors=frame[PTPDTimeSeriesProfile.COLUMN_STATIONARY_TEST_CONFIDENCE].map(
        #             lambda value: "green" if value > 0 else "red")
        #     )
