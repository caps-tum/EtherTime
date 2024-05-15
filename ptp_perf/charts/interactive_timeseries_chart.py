import math
from datetime import timedelta

from bokeh import plotting
from bokeh.embed import file_html
from bokeh.layouts import column, row
from bokeh.models import WheelZoomTool, BoxAnnotation, CustomJSTickFormatter, \
    DatetimeTicker, Slider, CustomJS, RangeSlider

from ptp_perf.models import Sample, PTPEndpoint
from ptp_perf.models.endpoint import TimeNormalizationStrategy
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

        normalization = TimeNormalizationStrategy.PROFILE_START
        data = endpoint.load_samples_to_series(
                Sample.SampleType.CLOCK_DIFF, converged_only=False, remove_clock_step=False,
                normalize_time=normalization
        )
        abs_data = data.abs()
        for abs_value in [True, False]:
            current_data = abs_data if abs_value else data

            label_suffix = "(Absolute)" if abs_value else ""
            scatter = figure.scatter(
                x=current_data.index, y=current_data * BOKEH_TIME_SCALE,
                marker='circle', size=7,
                fill_color="#1f77b455", line_color="#1f77b4aa",
                legend_label=f'Clock Offset {label_suffix}',
            )

            line = figure.line(
                x=current_data.index, y=current_data.rolling(window=timedelta(seconds=30), center=True).mean() * BOKEH_TIME_SCALE,
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
            right=(endpoint.normalize(endpoint.convergence_timestamp, normalization)).total_seconds() * BOKEH_TIME_SCALE, fill_alpha=0.1,
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


        x_multiplier = units.MILLISECONDS_TO_SECONDS
        x_limits = (0, data.index.max().total_seconds() * BOKEH_TIME_SCALE * x_multiplier)
        x_slider = RangeSlider(
            start=x_limits[0], end=x_limits[1],
            value=x_limits, step=1, title="X Range",
            margin = (10, 10, 10, 10)
        )
        # y_limits = (-5, math.log10(data.max() * 1.1 * BOKEH_TIME_SCALE))
        y_multiplier = units.MILLISECONDS_IN_SECOND
        y_limits = (0, data.max() * 1.1 * BOKEH_TIME_SCALE * BOKEH_TIME_SCALE * y_multiplier)
        y_slider = RangeSlider(
            start=y_limits[0], end=y_limits[1],
            value=y_limits, step=1, title="Y Range",
            margin=(10, 10, 10, 10)
        )

        callback_sliders_to_plot = CustomJS(args=dict(plot=figure, x_slider=x_slider, y_slider=y_slider), code=f"""
            // Update plot range from sliders
            plot.x_range.start = x_slider.value[0] / {x_multiplier};
            plot.x_range.end = Math.max(x_slider.value[1] / {x_multiplier}, plot.y_range.start + 1);
            // plot.y_range.start = Math.pow(y_slider.value[0], 10);
            // plot.y_range.end = Math.pow(y_slider.value[1], 10);
            plot.y_range.start = y_slider.value[0] / {y_multiplier};
            plot.y_range.end = Math.max(y_slider.value[1] / {y_multiplier}, plot.y_range.start + 1);
        """)

        # Attach the CustomJS callback to the sliders' value changes
        x_slider.js_on_change('value', callback_sliders_to_plot)
        y_slider.js_on_change('value', callback_sliders_to_plot)

        # Define a CustomJS callback to update sliders' values when plot range changes
        callback_plot_to_sliders = CustomJS(args=dict(plot=figure, x_slider=x_slider, y_slider=y_slider), code=f"""
            // Update sliders' values from plot range
            x_slider.value = [plot.x_range.start * {x_multiplier}, plot.x_range.end * {x_multiplier}];
            // y_slider.value = [Math.log(plot.y_range.start) / Math.log(10), Math.log(plot.y_range.end) / Math.log(10)];
            y_slider.value = [plot.y_range.start * {y_multiplier}, plot.y_range.end * {y_multiplier}];
        """)

        # Attach the CustomJS callback to the plot's range changes
        figure.x_range.js_on_change('start', callback_plot_to_sliders)
        figure.x_range.js_on_change('end', callback_plot_to_sliders)
        figure.y_range.js_on_change('start', callback_plot_to_sliders)
        figure.y_range.js_on_change('end', callback_plot_to_sliders)

        layout = column(figure, row(x_slider, y_slider))
        layout.sizing_mode = "stretch_both"

        return layout


    def render_to_html(self, endpoint: PTPEndpoint):
        figure = self.create(endpoint)
        return file_html(figure, "inline", "Timeseries Plot")