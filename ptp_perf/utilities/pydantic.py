from pathlib import Path

from pydantic import RootModel

from ptp_perf.util import PathOrStr


def pydantic_save_model(model, instance, path: PathOrStr):
    Path(path).write_text(RootModel[model](instance).model_dump_json(indent=4))


def pydantic_load_model(model, path: PathOrStr):
    return RootModel[model].model_validate_json(Path(path).read_text()).root
