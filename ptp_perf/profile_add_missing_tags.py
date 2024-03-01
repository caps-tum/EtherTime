from profiles.benchmark import Benchmark
from registry.benchmark_db import BenchmarkDB
from registry.resolve import ProfileDB


def add_missing_tags_all_profiles():
    db = ProfileDB()
    for profile in db.resolve_all():
        benchmark_definition: Benchmark = BenchmarkDB.get(profile.benchmark.id)
        for tag in benchmark_definition.tags:
            if tag not in profile.benchmark.tags:
                profile.benchmark.tags.append(tag)
                print(f"Added tag {tag} to {profile.id}")
        profile.save()


if __name__ == '__main__':
    add_missing_tags_all_profiles()
