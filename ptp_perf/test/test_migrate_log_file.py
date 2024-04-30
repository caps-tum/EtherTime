import unittest

from django.test import TestCase

from ptp_perf.adapters.resource_monitor import ResourceMonitor
from ptp_perf.models import LogRecord


class MigrateLogRecordSourceTest(unittest.TestCase):

    def test_migrate_log_record_source(self):
        records = LogRecord.objects.filter(source="root", message__startswith='{"system":')
        index = -1
        record: LogRecord
        for index, record in enumerate(records.iterator()):
            record.source = ResourceMonitor.log_source
            record.save()

            record.refresh_from_db()
            self.assertEqual(record.source, 'resource_monitor')

            if index % 100 == 0:
                print(f"Migrated {index + 1} log records.")
        print(f"Migrated {index+1} log records.")
