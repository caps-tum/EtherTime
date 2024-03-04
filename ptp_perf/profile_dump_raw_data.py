from argparse import ArgumentParser

from profiles.base_profile import BaseProfile
from ptp_perf.util import StackTraceGuard

if __name__ == '__main__':
    parser = ArgumentParser("Dump raw data from a profile.")
    parser.add_argument("profile_path", help="Path of the profile to fetch data from.")

    result = parser.parse_args()
    with StackTraceGuard():
        profile = BaseProfile.load(result.profile_path)

        for key, value in profile.raw_data.items():
            print(f"===== {key} =====")
            print(value)
