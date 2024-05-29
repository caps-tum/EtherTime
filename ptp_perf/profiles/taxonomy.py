from dataclasses import dataclass
from typing import ClassVar, Self


@dataclass(frozen=True)
class NamedItem:
    id: str
    name: str
    tag_basename: str

    @property
    def tag(self):
        return f"{self.tag_basename}_{self.id}"

    def __eq__(self, __value):
        return isinstance(__value, NamedItem) and self.id == __value.id

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return self.name


@dataclass(frozen=True)
class ResourceContentionType(NamedItem):
    tag_basename: str = "isolation"
    UNPRIORITIZED: ClassVar["Self"]
    PRIORITIZED: ClassVar["Self"]
    ISOLATED: ClassVar["Self"]

ResourceContentionType.UNPRIORITIZED = ResourceContentionType("unprioritized", "Unprioritized")
ResourceContentionType.PRIORITIZED = ResourceContentionType("prioritized", "Prioritized")
ResourceContentionType.ISOLATED = ResourceContentionType("isolated", "Isolated")


@dataclass(frozen=True)
class ResourceContentionComponent(NamedItem):
    tag_basename: str = "component"
    CPU: ClassVar["Self"]
    NET: ClassVar["Self"]
    AUX: ClassVar["Self"]

ResourceContentionComponent.CPU = ResourceContentionComponent("cpu", "CPU")
ResourceContentionComponent.NET = ResourceContentionComponent("net", "Network")
ResourceContentionComponent.AUX = ResourceContentionComponent("aux", "Auxiliary")
