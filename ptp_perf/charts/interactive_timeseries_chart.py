import math
from datetime import timedelta

from bokeh import plotting
from bokeh.embed import file_html
from bokeh.layouts import column
from bokeh.models import WheelZoomTool, BoxAnnotation, CustomJSTickFormatter, \
    DatetimeTicker, Slider, CustomJS

from ptp_perf.models import Sample, PTPEndpoint
from ptp_perf.utilities import units

BOKEH_TIME_SCALE = 1000


class InteractiveTimeseriesChart:

    def create(self, endpoint: PTPEndpoint):
        figure = plotting.figure(
            title=f"{endpoint}",
            x_axis_label="Time",
            y_axis_label="Clock Offset",
        )
        figure.sizing_mode = 'stretch_both'
        figure.toolbar.active_scroll = figure.select_one(WheelZoomTool)

        top_limit = 0
        for abs_value in [True, False]:
            data = endpoint.load_samples_to_series(
                Sample.SampleType.CLOCK_DIFF, converged_only=False, remove_clock_step=False,
                # normalize_time=TimeNormalizationStrategy.PROFILE_START
            )
            if abs_value:
                data = abs(data)
            top_limit = max(top_limit, data.max())

            label_suffix = "(Absolute)" if abs_value else ""
            scatter = figure.scatter(
                x=data.index, y=data * BOKEH_TIME_SCALE,
                marker='circle', size=7,
                fill_color="#1f77b455", line_color="#1f77b4aa",
                legend_label=f'Clock Offset {label_suffix}',
            )

            line = figure.line(
                x=data.index, y=data.rolling(window=timedelta(seconds=30), center=True).mean() * BOKEH_TIME_SCALE,
                line_width=5,
                legend_label=f'Rolling Clock Offset {label_suffix}',
            )

            if not abs_value:
                scatter.visible = False
                line.visible = False


        figure.legend.click_policy = 'hide'
        figure.legend.location = "top_right"

        # Box invalid data
        convergence_zone_annotation = BoxAnnotation(
            right=endpoint.convergence_duration.total_seconds() * BOKEH_TIME_SCALE, fill_alpha=0.1,
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

        top_limit *= 1.1
        # Create a slider widget
        top_value = math.log10(top_limit * BOKEH_TIME_SCALE)
        slider = Slider(start=-3, end=top_value, value=top_value, step=1 / BOKEH_TIME_SCALE, title="Y Range")

        # Define a CustomJS callback to update the y-range
        callback = CustomJS(args=dict(plot=figure, slider=slider), code="""
            var value = slider.value;
            plot.y_range.start = 0;
            plot.y_range.end = Math.pow(10, value);
        """)
        slider.js_on_change('value', callback)

        layout = column(figure, slider)
        layout.sizing_mode = "stretch_both"

        return layout


    def render_to_html(self, endpoint: PTPEndpoint):
        figure = self.create(endpoint)
        return file_html(figure, "inline", "Timeseries Plot")