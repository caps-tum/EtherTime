from dataclasses import dataclass, field
from typing import TypeVar, ClassVar, Dict, Any, Optional, Self

from constants import LOCAL_DIR
from utilities.pydantic import pydantic_save_model, pydantic_load_model

T = TypeVar("T")

@dataclass
class DataCache:
    cache: Optional[Dict[str, Any]] = field(default_factory=dict)
    cache_location: ClassVar[str]
    singleton: ClassVar[Optional[Self]]

    @classmethod
    def resolve(cls) -> Self:
        if cls.singleton is None:
            cls.singleton = pydantic_load_model(type(cls), cls.cache_location)
        return cls.singleton

    def get(self, key: str) -> T:
        return self.cache[key]

    def update(self, key: str, value: T):
        self.cache[key] = value
        pydantic_save_model(type(self), self, self.cache_location)


class SummaryStatisticCache(DataCache):
    cache_location = LOCAL_DIR.joinpath("summary_statistic_cache.json")
