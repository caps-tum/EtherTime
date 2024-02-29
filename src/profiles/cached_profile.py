from dataclasses import dataclass, field
from typing import List, Dict, Iterable, Optional

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
    cached_profiles: Dict[str, CachedProfile] = field(default_factory=list)
    """The cached values, indexed by file path (not id, cause they are not unique :/)"""

    @staticmethod
    def build(profiles: List[BaseProfile], persist: bool = False):
        cached_profiles = [CachedProfile.from_profile(profile) for profile in profiles]
        new_cache = ProfileCache(
            cached_profiles={ProfileCache.get_primary_key(cached_profile): cached_profile for cached_profile in cached_profiles}
        )
        if persist:
            new_cache.save()
        return new_cache

    def update(self, profile: BaseProfile, persist: bool = True):
        cached_profile = CachedProfile.from_profile(profile)
        self.cached_profiles[self.get_primary_key(cached_profile)] = cached_profile
        if persist:
            self.save()

    @staticmethod
    def load() -> "ProfileCache":
        return pydantic_load_model(ProfileCache, PROFILE_CACHE_LOCATION)

    def save(self):
        return pydantic_save_model(ProfileCache, self, PROFILE_CACHE_LOCATION)

    @staticmethod
    def invalidate():
        PROFILE_CACHE_LOCATION.unlink(missing_ok=True)

    def all(self) -> Iterable[CachedProfile]:
        return self.cached_profiles.values()

    @staticmethod
    def get_primary_key(profile: CachedProfile):
        return profile.profile_location

    def load_real_profile(self, cached_profile: CachedProfile) -> Optional[BaseProfile]:
        try:
            return cached_profile.load_profile()
        except FileNotFoundError:
            del self.cached_profiles[self.get_primary_key(cached_profile)]
            self.save()
            return None
