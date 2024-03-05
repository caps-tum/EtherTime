from datetime import datetime

from ptp_perf.utilities.django import bootstrap_django_environment

bootstrap_django_environment()

from ptp_perf.benchmark import get_server_datetime
from django.test import TestCase


class TestLogToDBLogRecordHandler(TestCase):

    def test_server_datetime(self):
        now = get_server_datetime()
        self.assertIsInstance(now, datetime)
