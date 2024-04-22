from django.test import TestCase

from ptp_perf.django_data.app.management.commands.analyze import run_analysis


class TestAnalyze(TestCase):

    def test_analyze(self):
        run_analysis(False)
