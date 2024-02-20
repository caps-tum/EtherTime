import logging
from pathlib import Path

import constants
import util
from profiles.base_profile import ProfileType
from registry import resolve
from registry.resolve import ProfileDB


def analyze():
    profile_db = ProfileDB()
    for profile in profile_db.resolve_all(resolve.BY_TYPE(ProfileType.RAW)):

        logging.info(f"Converting {profile.file_path_relative}")
        processed = profile.vendor.convert_profile(profile)
        if processed is not None:
            processed.save()


if __name__ == '__main__':
    util.setup_logging(log_file=constants.CHARTS_DIR.joinpath("analysis_log.log"), log_file_mode="w")

    with util.StackTraceGuard():
        analyze()
