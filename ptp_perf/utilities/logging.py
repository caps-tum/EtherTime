import logging
import os
from queue import Queue
from threading import Thread

from ptp_perf.models import PTPEndpoint, LogRecord
from ptp_perf.utilities.django_utilities import get_server_datetime


class LogToDBLogRecordHandler(logging.Handler):
    endpoint: PTPEndpoint
    queue: Queue[LogRecord]
    thread: Thread

    def __init__(self, endpoint: PTPEndpoint, level=0):
        super().__init__(level)
        self.endpoint = endpoint
        # self.queue = Queue(maxsize=20)
        # self.thread = Thread(self._run_db_save(), name="Log to DB save thread")
        # self.thread.start()


    def emit(self, record: logging.LogRecord):
        db_record = LogRecord(
            timestamp=get_server_datetime(),
            endpoint=self.endpoint,
            source=record.name,
            message=self.format(record)
        )
        db_record.save()


    def _run_db_save(self):
        while True:
            item: LogRecord = self.queue.get()
            item.save()


    def install(self):
        """Sets allow unsafe async for this to work :/"""

        # Cannot run save/time query from synchronous function within asynchronous context if this is unset :/
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
        logging.root.addHandler(self)

    def uninstall(self):
        logging.root.removeHandler(self)
