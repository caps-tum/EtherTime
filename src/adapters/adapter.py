import logging
from datetime import datetime

from profiles.base_profile import BaseProfile


class Adapter:
    profile: BaseProfile
    raw_data_log_key: str = ""
    _log_history: str = ""

    def __init__(self, profile: BaseProfile):
        super().__init__()
        self.profile = profile

    def log(self, message: str):
        output = f"{datetime.now()}: {message}"
        self._log_history += output + "\n"
        logging.info(output)

    def export_log(self):
        return {
            self.raw_data_log_key: self._log_history
        }

    def run_and_collect(self):
        try:
            self.run()
        finally:
            if self._log_history is not None:
                self.profile.raw_data.update(**self.export_log())

    def run(self):
        raise NotImplementedError()
