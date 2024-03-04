import logging
from datetime import datetime, timezone

from ptp_perf.util import setup_logging
from ptp_perf.utilities.django import bootstrap_django_environment

bootstrap_django_environment()

from django.test import TestCase
from ptp_perf.models import PTPProfile
from ptp_perf.models import LogRecord, PTPEndpoint
from ptp_perf.utilities.logging import LogToDBLogRecordHandler


class TestLogToDBLogRecordHandler(TestCase):


    def test_emit(self):
        setup_logging()

        # Logging shouldn't do anything when nothing installed
        self.assertEqual(0, LogRecord.objects.count())
        logging.info("Test log")
        self.assertEqual(0, LogRecord.objects.count())

        profile = PTPProfile.objects.create(benchmark_id="test-benchmark", vendor_id="test-vendor", start_time=datetime.now(timezone.utc), stop_time=datetime.now(timezone.utc))
        endpoint = PTPEndpoint.objects.create(profile=profile, machine_id="test")

        # Install handler
        handler = LogToDBLogRecordHandler(endpoint)
        handler.install()

        # Message should be captured
        logging.info("This is a test message")
        self.assertEqual(1, LogRecord.objects.count())
        self.assertIn("test message", LogRecord.objects.get().message)

        # Logging to specific logger
        logging.getLogger("test_module").info("Test module message")
        self.assertEqual(2, LogRecord.objects.count())
        self.assertIn("Test module message", LogRecord.objects.get(id=2).message)
        self.assertIn("test_module", LogRecord.objects.get(id=2).source)


        handler.uninstall()

        # Should no longer be captured.
        logging.info("Test log 2")
        self.assertEqual(2, LogRecord.objects.count())
