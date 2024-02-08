from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

import constants
from machine import Machine
from profiles.base_profile import BaseProfile, ProfileType
from profiles.benchmark import Benchmark
from vendor.vendor import Vendor

PROFILE_FILTER = Callable[[BaseProfile], bool]

@dataclass
class ProfileDB:
    base_directory: Path = constants.MEASUREMENTS_DIR

    def find_profile_paths(self) -> List[Path]:
        return list(self.base_directory.rglob("*.json"))

    def load_profiles(self) -> List[BaseProfile]:
        return [BaseProfile.load(profile_path) for profile_path in self.find_profile_paths()]

    def resolve_all(self, *filters: PROFILE_FILTER) -> List[BaseProfile]:
        if filters is None:
            filters = []
        return [profile for profile in self.load_profiles() if all(filter_function(profile) for filter_function in filters)]

    def resolve_most_recent(self, *filters: PROFILE_FILTER) -> Optional[BaseProfile]:
        try:
            return sorted(
                self.resolve_all(*filters),
                key=lambda profile: profile.start_time
            )[-1]
        except IndexError:
            return None

    def default_save_location(self, profile: BaseProfile):
        return self.base_directory.joinpath(profile.filename)

def VALID_PROCESSED_PROFILE():
    return lambda profile: profile.profile_type == ProfileType.PROCESSED and not profile.time_series.empty

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
