import os
from pathlib import Path


def get_repository_root() -> Path:
    repository_location = Path(os.path.realpath(__file__)).parent.parent
    if repository_location.joinpath("pyproject.toml").exists():
        return repository_location
    raise RuntimeError(f"Failed to resolve repository root: {repository_location}.")

MEASUREMENTS_DIR = get_repository_root().joinpath("measurements_raw")
CHARTS_DIR = get_repository_root().joinpath("measurements_charts")
