import logging
import typing
from contextlib import asynccontextmanager
from dataclasses import dataclass

if typing.TYPE_CHECKING:
    from profiles.base_profile import BaseProfile


@dataclass()
class BenchmarkAdapter:
    priority: int = 10
    """A priority is used to ensure that adapters are executed in a specific order.
    Adapters with lower priority will be setup earlier and shutdown later."""

    async def setup(self):
        await self.on_setup()

    async def on_setup(self):
        """Called before conducting any benchmarks. **NOTE: Currently not supported on PTP-Perf**"""
        pass

    async def on_pre_benchmark(self, profile: "BaseProfile"):
        """Called immediately before running specified benchmark"""
        pass

    async def on_pre_benchmark_worker(self, profile: "BaseProfile"):
        """Called immediately before running specified benchmark, on each worker"""
        pass

    async def on_post_benchmark_worker(self, profile: "BaseProfile"):
        """Called immediately after running a benchmark, on each worker
        :param config:
        """
        pass

    async def on_post_benchmark(self, profile: "BaseProfile"):
        """Called immediately after running a benchmark
        :param config:
        """
        pass

    async def on_teardown(self):
        """Called after all benchmarks have run. **NOTE: Currently not supported on PTP-Perf**"""
        pass

    def __str__(self):
        return self.__class__.__name__

    @asynccontextmanager
    async def global_context_manager(self):
        try:
            logging.debug(f"{self.__class__.__name__}: on_setup")
            await self.setup()

            yield
        finally:
            logging.debug(f"{self.__class__.__name__}: on_teardown")
            await self.on_teardown()

    @asynccontextmanager
    async def benchmark_context_manager(self, profile: "BaseProfile"):
        try:
            logging.debug(f"{self.__class__.__name__}: on_pre_benchmark")
            await self.on_pre_benchmark(profile)

            yield
        finally:
            logging.debug(f"{self.__class__.__name__}: on_post_benchmark")
            await self.on_post_benchmark(profile)
