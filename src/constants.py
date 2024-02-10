import os
from pathlib import Path


def get_repository_root() -> Path:
    repository_location = Path(os.path.realpath(__file__)).parent.parent
    if repository_location.joinpath("pyproject.toml").exists():
        return repository_location
    raise RuntimeError(f"Failed to resolve repository root: {repository_location}.")

PTPPERF_REPOSITORY_ROOT = get_repository_root()
MEASUREMENTS_DIR = PTPPERF_REPOSITORY_ROOT.joinpath("data").joinpath("profiles")
CHARTS_DIR = PTPPERF_REPOSITORY_ROOT.joinpath("data").joinpath("charts")
CONFIG_DIR = PTPPERF_REPOSITORY_ROOT.joinpath("data").joinpath("config")
LOCAL_DIR = PTPPERF_REPOSITORY_ROOT.joinpath("local")
