import datetime

from bokeh.models import DatetimeTickFormatter

from profiles.base_profile import BaseProfile
from bokeh import plotting

class InterativeTimeseriesChart:

    def create(self, profile: BaseProfile):

        figure = plotting.figure(
            title=profile.id,
            x_axis_label="Time",
            y_axis_label="Clock Offset",
        )

        data = profile.time_series.get_clock_diff(abs=True)
        figure.circle(
            x=data.index, y=data,
            fill_color="#aaaaaa", line_color="#666666",
        )

        figure.line(
            x=data.index, y=data.rolling(window=datetime.timedelta(seconds=30), center=True).mean()
        )

        figure.yaxis[0].formatter = DatetimeTickFormatter()
        figure.xaxis[0].formatter = DatetimeTickFormatter()

        return figure
