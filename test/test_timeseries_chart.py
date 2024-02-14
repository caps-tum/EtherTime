from pathlib import Path
from unittest import TestCase

import constants
from charts.timeseries_chart import TimeseriesChart
from charts.timeseries_chart_comparison import TimeSeriesChartComparison
from charts.timeseries_chart_versus import TimeSeriesChartVersus
from registry import resolve
from registry.benchmark_db import BenchmarkDB
from registry.resolve import ProfileDB
from vendor.registry import VendorDB


class TestTimeseriesChart(TestCase):
    # def test_create(self):
    #     profile = PTPDTimeSeriesProfile.load_str(TEST_TIMESERIES_PROFILE)
    #     chart = TimeseriesChart()
    #     chart.create(profile)
    #     chart.save("test-series.png")

    def test_individual_charts(self):
        profiles = ProfileDB().resolve_all(resolve.VALID_PROCESSED_PROFILE())
        profiles += ProfileDB().resolve_all(resolve.CORRUPT_PROCESSED_PROFILE())

        for profile in profiles:
            profile_path = Path(profile._file_path)

            # We create multiple charts:
            # one only showing the filtered data, one showing the convergence, and one including the path delay
            if profile.time_series is not None:
                chart =  TimeseriesChart(
                    title=profile.get_title(),
                    timeseries=profile.time_series,
                    summary_statistics=profile.summary_statistics,
                )
                chart.add_clock_difference(profile.time_series)
                chart.save(profile_path.parent.joinpath(f"{profile_path.stem}-series.png"))

                chart =  TimeseriesChart(
                    title=profile.get_title("with Path Delay"),
                    timeseries=profile.time_series,
                    summary_statistics=profile.summary_statistics,
                )
                chart.add_path_delay(profile.time_series)
                chart.add_clock_difference(profile.time_series)
                chart.save(profile_path.parent.joinpath(f"{profile_path.stem}-series-path-delay.png"))

            if profile.time_series_unfiltered is not None:
                chart_convergence = TimeseriesChart(
                    title=profile.get_title("with Convergence"),
                    timeseries=profile.time_series_unfiltered,
                    summary_statistics=profile.convergence_statistics,
                )
                chart_convergence.add_clock_difference(profile.time_series_unfiltered)
                chart_convergence.add_path_delay(profile.time_series_unfiltered)
                if profile.convergence_statistics is not None:
                    chart_convergence.add_boundary(chart_convergence.axes[0], profile.convergence_statistics.convergence_time)
                chart_convergence.save(profile_path.parent.joinpath(f"{profile_path.stem}-series-unfiltered.png"))

    def test_comparison(self):
        ptpd_profile = ProfileDB().resolve_most_recent(
            resolve.VALID_PROCESSED_PROFILE(),
            resolve.BY_BENCHMARK(BenchmarkDB.BASE),
            resolve.BY_VENDOR(VendorDB.PTPD),
        )
        linuxptp_profile = ProfileDB().resolve_most_recent(
            resolve.VALID_PROCESSED_PROFILE(),
            resolve.BY_BENCHMARK(BenchmarkDB.BASE),
            resolve.BY_VENDOR(VendorDB.LINUXPTP),
        )

        if ptpd_profile is None or linuxptp_profile is None:
            self.skipTest("Required profile not found")
            return

        chart = TimeSeriesChartVersus(ptpd_profile, linuxptp_profile)
        chart.set_titles("PTPd", "LinuxPTP")
        chart.save(constants.CHARTS_DIR.joinpath("vendors").joinpath("ptpd-vs-linuxptp.png"), make_parent=True)

    def test_history(self):
        self.create_history_charts(BenchmarkDB.BASE)

    def create_history_charts(self, benchmark, y_log=False):
        for vendor in VendorDB.all():
            profiles = ProfileDB().resolve_all(
                resolve.VALID_PROCESSED_PROFILE(),
                resolve.BY_BENCHMARK(benchmark),
                resolve.BY_VENDOR(vendor)
            )

            if not profiles:
                continue

            chart = TimeSeriesChartComparison(
                profiles,
                [f"#{index+1}: {profile.start_time.replace(second=0, microsecond=0)}" for index, profile in enumerate(profiles)],
                x_label="Profile Date",
            )
            if y_log:
                chart.axes[0].set_yscale('log')
                chart.axes[1].set_yscale('log')
            chart.axes[0].set_title(f"Profile History: {benchmark.name} using {vendor}")
            chart.save(constants.CHARTS_DIR.joinpath("history").joinpath(f"{benchmark.id}-history-{vendor}.png"),
                       make_parent=True)

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
