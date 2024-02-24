from dataclasses import dataclass, field
from typing import List

from pydantic import RootModel

from constants import LOCAL_DIR
from utilities.pydantic import pydantic_save_model, pydantic_load_model

PROFILE_CACHE_LOCATION = LOCAL_DIR.joinpath("profile_cache.json")
from profiles.base_profile import BaseProfile


@dataclass(kw_only=True)
class CachedProfile(BaseProfile):

    profile_location: str

    def load_profile(self):
        return BaseProfile.load(self.profile_location)

    @staticmethod
    def from_profile(profile: BaseProfile):
        return CachedProfile(
            id=profile.id,
            benchmark=profile.benchmark,
            vendor_id=profile.vendor_id,
            profile_type=profile.profile_type,
            machine_id=profile.machine_id,
            profile_location=str(profile.file_path),
            configuration=profile.configuration,
        )


@dataclass(kw_only=True)
class ProfileCache:
    cached_profiles: List[CachedProfile] = field(default_factory=list)

    @staticmethod
    def build(profiles: List[BaseProfile], persist: bool = False):
        new_cache = ProfileCache(cached_profiles=[CachedProfile.from_profile(profile) for profile in profiles])
        if persist:
            new_cache.save()
        return new_cache

    @staticmethod
    def load() -> "ProfileCache":
        return pydantic_load_model(ProfileCache, PROFILE_CACHE_LOCATION)

    def save(self):
        return pydantic_save_model(ProfileCache, self, PROFILE_CACHE_LOCATION)

    def invalidate(self):
        PROFILE_CACHE_LOCATION.unlink(missing_ok=True)
