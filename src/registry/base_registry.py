import re
from typing import TypeVar, Generic, Dict, List

T = TypeVar("T")

class BaseRegistry(Generic[T]):
    registered_entries: Dict[str, T] = None

    @classmethod
    def get(cls, id: str) -> T:
        return cls.all_by_id()[id]

    @classmethod
    def all_by_id(cls) -> Dict[str, T]:
        return cls.registered_entries

    @classmethod
    def all(cls):
        return cls.all_by_id().values()

    @classmethod
    def register(cls, value: T) -> T:
        if cls.registered_entries is None:
            cls.registered_entries = {}
        cls.registered_entries[value.id] = value
        return value

    @classmethod
    def register_all(cls, *values: T):
        for value in values:
            cls.register(value)

    @classmethod
    def get_by_regex(cls, regex: str) -> List[T]:
        return [value for key, value in cls.all_by_id().items() if re.match(regex, key)]
