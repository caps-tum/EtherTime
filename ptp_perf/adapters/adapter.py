import asyncio
from asyncio import CancelledError
from datetime import timedelta

from ptp_perf.models import PTPEndpoint


class Adapter:
    """A generic adapter class for running tasks while benchmarking. This class is meant to be subclassed."""
    endpoint: PTPEndpoint
    log_source: str = None

    def __init__(self, endpoint: PTPEndpoint):
        super().__init__()
        self.endpoint = endpoint

    def log(self, message: str):
        self.endpoint.log(message, self.log_source)

    def run(self):
        raise NotImplementedError()


class IntervalActionAdapter(Adapter):
    """An adapter that runs a task at a fixed interval. This class is meant to be subclassed."""
    interval: timedelta = timedelta(seconds=1)

    async def run(self):
        try:
            while True:
                await self.update()
                await asyncio.sleep(1)
        except CancelledError:
            pass

    async def update(self):
        raise NotImplementedError()
