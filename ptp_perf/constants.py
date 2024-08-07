import os
from datetime import timedelta
from pathlib import Path

from ptp_perf.utilities import units


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
DATASET_DIR = ensure_directory_exists(PTPPERF_REPOSITORY_ROOT.joinpath("dataset"))
MEASUREMENTS_DIR = ensure_directory_exists(DATA_DIR.joinpath("profiles"))
CHARTS_DIR = ensure_directory_exists(DATA_DIR.joinpath("charts"))
CONFIG_DIR = ensure_directory_exists(DATA_DIR.joinpath("config"))

LOCAL_DIR = ensure_directory_exists(PTPPERF_REPOSITORY_ROOT.joinpath("local"))
PAPER_GENERATED_RESOURCES_DIR = PTPPERF_REPOSITORY_ROOT.joinpath("doc").joinpath("project-4-paper").joinpath("paper").joinpath("res").joinpath("generated")

DEFAULT_BENCHMARK_DURATION = timedelta(minutes=20)


RPI_CHART_DISPLAY_LIMIT = 50000 * units.NANOSECONDS_TO_SECONDS
