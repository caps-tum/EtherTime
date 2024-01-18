import util
from profiles.base_profile import ProfileType
from registry import resolve
from registry.resolve import ProfileDB


def analyze():
    profile_db = ProfileDB()
    for profile in profile_db.resolve_all(resolve.BY_TYPE(ProfileType.RAW)):

        processed = profile.vendor.convert_profile(profile)
        if processed is not None:
            print(f"Converting {profile.filename}")
            processed.save(profile_db.base_directory.joinpath(processed.filename))


if __name__ == '__main__':
    util.setup_logging()

    with util.StackTraceGuard():
        analyze()
