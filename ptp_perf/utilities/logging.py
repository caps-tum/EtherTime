import logging
from datetime import datetime

from ptp_perf.models import PTPEndpoint, LogRecord


class LogToDBLogRecordHandler(logging.Handler):
    endpoint: PTPEndpoint

    def __init__(self, endpoint: PTPEndpoint, level=0):
        super().__init__(level)
        self.endpoint = endpoint

    def emit(self, record: logging.LogRecord):
        db_record = LogRecord(
            timestamp=datetime.fromtimestamp(record.created),
            endpoint=self.endpoint,
            source=record.name,
            message=self.format(record)
        )
        db_record.save()

    def install(self):
        logging.root.addHandler(self)

    def uninstall(self):
        logging.root.removeHandler(self)
