import logging
from datetime import datetime

from ptp_perf.models import PTPEndpoint
from ptp_perf.profiles.base_profile import BaseProfile


class Adapter:
    endpoint: PTPEndpoint
    log_source: str = None

    def __init__(self, endpoint: PTPEndpoint):
        super().__init__()
        self.endpoint = endpoint

    def log(self, message: str):
        self.endpoint.log(message, self.log_source)

    def run(self):
        raise NotImplementedError()
