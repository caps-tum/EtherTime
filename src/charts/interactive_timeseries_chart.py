from datetime import timedelta

from bokeh import plotting
from bokeh.models import WheelZoomTool, BoxAnnotation, CustomJSTickFormatter, \
    DatetimeTicker

from profiles.base_profile import BaseProfile

BOKEH_TIME_SCALE = 1000


class InterativeTimeseriesChart:

    def create(self, profile: BaseProfile):
        figure = plotting.figure(
            title=profile.id,
            x_axis_label="Time",
            y_axis_label="Clock Offset",
        )
        figure.sizing_mode = 'stretch_both'
        figure.toolbar.active_scroll = figure.select_one(WheelZoomTool)

        for abs_value in [True, False]:
            data = profile.time_series_unfiltered.get_clock_diff(abs=abs_value)
            label_suffix = "(Absolute)" if abs_value else ""
            scatter = figure.circle(
                x=data.index, y=data * BOKEH_TIME_SCALE,
                fill_color="#aaaaaa", line_color="#666666",
                legend_label=f'Clock Offset {label_suffix}',
            )

            line = figure.line(
                x=data.index, y=data.rolling(window=timedelta(seconds=30), center=True).mean() * BOKEH_TIME_SCALE,
                legend_label=f'Rolling Clock Offset {label_suffix}',
            )

            if not abs_value:
                scatter.visible = False
                line.visible = False


        figure.legend.click_policy = 'hide'
        figure.legend.location = "top_right"

        # Box invalid data
        convergence_zone_annotation = BoxAnnotation(
            right=profile.convergence_statistics.convergence_time.total_seconds() * BOKEH_TIME_SCALE, fill_alpha=0.1,
            fill_color='#D55E00'
        )
        figure.add_layout(convergence_zone_annotation)

        formatter = CustomJSTickFormatter(code="""
        let prescale=1000 * 1000;
        let factors=[60 * 60 * 1000 * 1000 * 1000, 60 * 1000 * 1000 * 1000 , 1000 * 1000 * 1000, 1000 * 1000, 1000, 1];
        let labels=["h", "m", "s", "ms", "us", "ns"];
        let tick_str = "";
        let remainder = Math.floor(Math.abs(tick) * prescale);
        if(tick < 0) {
            tick_str += "-";
        } else if(tick == 0) {
            tick_str += "0";
        }
        for(let i = 0; i < factors.length; i++) {
            if(remainder >= factors[i]) {
                let divisor = Math.floor(remainder / factors[i]);
                remainder = remainder % factors[i];
                tick_str += divisor + labels[i];
            }
        }
        return tick_str;
        """)
        # formatter = DatetimeTickFormatter()

        figure.yaxis[0].formatter = formatter
        figure.xaxis[0].formatter = formatter
        figure.yaxis[0].ticker = DatetimeTicker()
        figure.xaxis[0].ticker = DatetimeTicker()

        return figure
