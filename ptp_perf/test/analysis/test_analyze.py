from django.test import TestCase

from ptp_perf.django_data.app.management.commands.analyze import run_analysis
from ptp_perf.util import setup_logging


class TestAnalyze(TestCase):

    def test_analyze(self):
        setup_logging()
        run_analysis(False)
