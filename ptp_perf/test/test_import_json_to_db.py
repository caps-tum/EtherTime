from django.test import TestCase

from ptp_perf.models import PTPProfile, PTPEndpoint
from ptp_perf.profiles.base_profile import ProfileType
from ptp_perf.registry import resolve


class ImportTest(TestCase):

    def test_import(self):
        self.skipTest("Disabled")

        for raw_profile in ProfileDB().resolve_all(resolve.BY_TYPE(ProfileType.RAW)):
            try:
                profile = PTPProfile.objects.filter(start_time=raw_profile.start_time).get()
                assert profile.benchmark_id == raw_profile.benchmark.id
                assert profile.vendor_id == raw_profile.vendor_id
            except PTPProfile.DoesNotExist:
                profile = PTPProfile(
                    benchmark_id=raw_profile.benchmark.id,
                    vendor_id=raw_profile.vendor_id,
                    is_successful=raw_profile.success,
                    start_time=raw_profile.start_time,
                )
                profile.save()

            try:
                endpoint = PTPEndpoint.objects.filter(profile=profile, machine_id=raw_profile.machine_id).get()
                # Should not have an endpoint yet
                assert False
            except PTPEndpoint.DoesNotExist:
                endpoint = PTPEndpoint(
                    profile=profile,
                    machine_id=raw_profile.machine_id,
                )
                endpoint.save()

            # for log_line in raw_profile.raw_data[""]