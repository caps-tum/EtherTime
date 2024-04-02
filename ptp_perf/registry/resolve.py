from ptp_perf.machine import Machine
from ptp_perf.profiles.base_profile import ProfileType
from ptp_perf.profiles.benchmark import Benchmark
from ptp_perf.vendor.vendor import Vendor

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
