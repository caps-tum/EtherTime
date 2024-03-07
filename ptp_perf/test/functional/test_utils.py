from datetime import datetime

from ptp_perf.utilities.django_utilities import bootstrap_django_environment, get_server_datetime

bootstrap_django_environment()

from django.test import TestCase


class TestLogToDBLogRecordHandler(TestCase):

    def test_server_datetime(self):
        now = get_server_datetime()
        self.assertIsInstance(now, datetime)
