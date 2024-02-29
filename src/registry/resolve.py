import glob
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, ClassVar, Iterable

import constants
from machine import Machine
from profiles.base_profile import BaseProfile, ProfileType
from profiles.benchmark import Benchmark
from profiles.cached_profile import ProfileCache
from vendor.vendor import Vendor

PROFILE_FILTER = Callable[[BaseProfile], bool]

@dataclass
class ProfileDB:
    base_directory: Path = constants.MEASUREMENTS_DIR
    _profile_cache: ClassVar[ProfileCache] = None

    def find_profile_paths(self) -> Iterable[str]:
        # Optimization: Path.rglob is quite slow until Python 3.12/3.13
        # Faster to iterate by string.
        # https://github.com/python/cpython/issues/102613
        base_path_as_str = str(self.base_directory)
        for result in glob.glob("**/*.json", root_dir=self.base_directory, recursive=True):
            yield base_path_as_str + '/' + result

    def update_cache(self):
        cache = self.get_cache()
        for path in self.find_profile_paths():
            if path not in cache.cached_profiles.keys():
                cache.update(BaseProfile.load(path), persist=False)
        cache.save()

    def get_cache(self) -> ProfileCache:
        if ProfileDB._profile_cache is None:
            try:
                ProfileDB._profile_cache = ProfileCache.load()
            except FileNotFoundError:
                logging.info("Building profile cache...")
                ProfileDB._profile_cache = ProfileCache.build(
                    [BaseProfile.load(profile_path) for profile_path in self.find_profile_paths()],
                    persist=True
                )
                logging.info(f"Built profile cache: {len(self._profile_cache.cached_profiles)} profiles cached.")
        return ProfileDB._profile_cache

    def invalidate_cache(self):
        self.get_cache().invalidate()
        ProfileDB._profile_cache = None

    def resolve_all(self, *filters: PROFILE_FILTER) -> List[BaseProfile]:
        if filters is None:
            filters = []

        cached_profile = self.get_cached_profiles(filters)
        # Some profiles might have been deleted, remove those from results
        real_profiles = [profile.load_profile() for profile in cached_profile]
        return [profile for profile in real_profiles if profile is not None]

    def get_cached_profiles(self, filters):
        return [profile for profile in self.get_cache().all() if
                all(filter_function(profile) for filter_function in filters)]

    def resolve_most_recent(self, *filters: PROFILE_FILTER) -> Optional[BaseProfile]:
        cached_profiles = self.get_cached_profiles(filters)
        for cached_profile in sorted(cached_profiles, key=lambda profile: profile.start_time, reverse=True):
            real_profile = cached_profile.load_profile()
            if real_profile is not None:
                return real_profile

        return None

def VALID_PROCESSED_PROFILE():
    return lambda profile: profile.profile_type == ProfileType.PROCESSED

def CORRUPT_PROCESSED_PROFILE():
    return lambda profile: profile.profile_type == ProfileType.PROCESSED_CORRUPT

def AGGREGATED_PROFILE():
    return lambda profile: profile.profile_type == ProfileType.AGGREGATED

def BY_BENCHMARK(benchmark: Benchmark):
    return lambda profile: profile.benchmark.id == benchmark.id

def BY_VENDOR(vendor: Vendor):
    return lambda profile: profile.vendor_id == vendor.id

def BY_TYPE(profile_type: str):
    return lambda profile: profile.profile_type == profile_type

def BY_TAGS(*tags: str):
    return lambda profile: all(tag in profile.benchmark.tags for tag in tags)

def BY_MACHINE(machine: Machine):
    return lambda profile: profile.machine_id == machine.id

def BY_VALID_BENCHMARK_AND_VENDOR(benchmark: Benchmark, vendor: Vendor):
    return lambda profile: VALID_PROCESSED_PROFILE()(profile) and BY_BENCHMARK(benchmark)(profile) and BY_VENDOR(vendor)(profile)

def BY_AGGREGATED_BENCHMARK_AND_VENDOR(benchmark: Benchmark, vendor: Vendor):
    return lambda profile: AGGREGATED_PROFILE()(profile) and BY_BENCHMARK(benchmark)(profile) and BY_VENDOR(vendor)(profile)
