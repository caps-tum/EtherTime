import os
from datetime import timedelta
from pathlib import Path


def get_repository_root() -> Path:
    repository_location = Path(os.path.realpath(__file__)).parent.parent
    if repository_location.joinpath("pyproject.toml").exists():
        return repository_location
    raise RuntimeError(f"Failed to resolve repository root: {repository_location}.")

def ensure_directory_exists(path: Path) -> Path:
    path.mkdir(exist_ok=True)
    return path

PTPPERF_REPOSITORY_ROOT = get_repository_root()

DATA_DIR = ensure_directory_exists(PTPPERF_REPOSITORY_ROOT.joinpath("data"))
MEASUREMENTS_DIR = ensure_directory_exists(DATA_DIR.joinpath("profiles"))
CHARTS_DIR = ensure_directory_exists(DATA_DIR.joinpath("charts"))
CONFIG_DIR = ensure_directory_exists(DATA_DIR.joinpath("config"))

LOCAL_DIR = ensure_directory_exists(PTPPERF_REPOSITORY_ROOT.joinpath("local"))

DEFAULT_BENCHMARK_DURATION = timedelta(minutes=20)
