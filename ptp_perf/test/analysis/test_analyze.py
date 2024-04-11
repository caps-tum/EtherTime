import unittest
from unittest import TestCase

from ptp_perf.utilities.django_utilities import bootstrap_django_environment


class TestAnalyze(TestCase):

    def test_analyze(self):
        bootstrap_django_environment()

        from ptp_perf.django_data.app.management.commands.analyze import analyze
        analyze()