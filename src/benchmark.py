import asyncio
import logging
import time

from config import current_configuration
from profiles.base_profile import BaseProfile
from vendor.registry import VendorDB


async def prepare():
    for vendor in VendorDB.all():
        await vendor.stop()


async def benchmark(profile: BaseProfile):

    profile.machine_id = current_configuration.machine.id

    try:
        logging.info(f"Starting {profile.vendor}...")
        await profile.vendor.start()
        logging.info(f"Benchmarking for {profile.benchmark.duration}...")
        await asyncio.sleep(profile.benchmark.duration.total_seconds())
    finally:
        await profile.vendor.stop()
        logging.info(f"Stopped {profile.vendor}...")

    profile.vendor.collect_data(profile)
    return profile
