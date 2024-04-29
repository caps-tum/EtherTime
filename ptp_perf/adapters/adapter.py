import asyncio
from asyncio import CancelledError
from datetime import timedelta

from ptp_perf.models import PTPEndpoint


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


class IntervalActionAdapter(Adapter):
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
