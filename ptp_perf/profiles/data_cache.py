from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar, ClassVar, Dict, Any, Optional, Self

from ptp_perf.constants import LOCAL_DIR
from ptp_perf.utilities.pydantic import pydantic_save_model, pydantic_load_model

T = TypeVar("T")

@dataclass
class DataCache:
    cache: Optional[Dict[str, Any]] = field(default_factory=dict)
    cache_location: ClassVar[str] = None
    singleton: ClassVar[Optional[Self]] = None

    @classmethod
    def resolve(cls) -> Self:
        if cls.singleton is None:
            if Path(cls.cache_location).exists():
                cls.singleton = pydantic_load_model(cls, cls.cache_location)
            else:
                cls.singleton = cls()
        return cls.singleton

    def get(self, key: str) -> T:
        return self.cache[key]

    def update(self, key: str, value: T):
        self.cache[key] = value
        pydantic_save_model(type(self), self, self.cache_location)

    def purge(self):
        self.cache.clear()
        Path(self.cache_location).unlink(missing_ok=True)


class SummaryStatisticCache(DataCache):
    cache_location = LOCAL_DIR.joinpath("summary_statistic_cache.json")
