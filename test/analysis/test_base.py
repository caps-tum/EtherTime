from unittest import TestCase

from profiles.base_profile import ProfileType
from profiles.aggregated_profile import AggregatedProfile
from registry import resolve
from registry.benchmark_db import BenchmarkDB
from registry.resolve import ProfileDB
from vendor.registry import VendorDB


class TestBase(TestCase):

    def test_analyze(self):
        profile = ProfileDB().resolve_most_recent(resolve.BY_TYPE(ProfileType.RAW), resolve.BY_BENCHMARK(BenchmarkDB.BASE), resolve.BY_VENDOR(VendorDB.LINUXPTP))
        profile.vendor.convert_profile(profile)

    def test_merge(self):
        profiles = ProfileDB().resolve_all(resolve.BY_VALID_BENCHMARK_AND_VENDOR(BenchmarkDB.BASE, VendorDB.LINUXPTP))
        AggregatedProfile.from_profiles(profiles)
