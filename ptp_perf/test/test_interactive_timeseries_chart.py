import re
from pathlib import Path
from unittest import TestCase

import bokeh.util.serialization
from bokeh import plotting

from ptp_perf.charts.interactive_timeseries_chart import InteractiveTimeseriesChart


class TestInteractiveTimeseriesChart(TestCase):
    def test_create(self):
        self.skipTest("Disabled for now.")

        chart = InteractiveTimeseriesChart()
        profile_db = ProfileDB()
        profiles = profile_db.resolve_all(resolve.VALID_PROCESSED_PROFILE())
        for profile in profiles:
            # Reset bokeh's id count
            bokeh.util.serialization._simple_id = 999
            figure = chart.create(profile)
            output_file = profile.storage_base_path.joinpath("interactive").joinpath(f"{profile.filename_base}.html")
            plotting.save(
                figure,
                filename=output_file,
                resources="cdn",
                title=f"{profile.id}",
            )

            # Post process the output files replacing random UUIDs with predictable ones.
            contents = output_file.read_text()
            replacements = {}
            for match in re.finditer('(?i)"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"', contents):
                match_string = match.group(0)
                if match_string not in replacements.keys():
                    replacements[match_string] = f'"{output_file.stem}-id-{len(replacements)}"'

            for search, replace in replacements.items():
                contents = contents.replace(search, replace)

            output_file.write_text(contents)
