import enum
import sys
from collections.abc import (
    Hashable,
    Iterable,
)
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    TypeVar,
)

from .constants import (
    SUFFIX_LOCKED,
    SUFFIX_UNLOCKED,
)

if sys.version_info >= (3, 10):  # pragma: no cover py-gte-310-else
    from typing import TypeAlias
else:  # pragma: no cover py-gte-310
    from typing_extensions import TypeAlias

DC_SLOTS: dict[str, bool]

__all__ = (
    "DATUM",
    "DatumByPkg",
    "InFileType",
    "OutLastSuffix",
    "PinDatum",
    "is_pin",
    "has_qualifiers",
    "pprint_pins",
)

def is_pin(specifiers: list[str]) -> bool: ...
def has_qualifiers(qualifiers: list[str]) -> bool: ...
def _parse_qualifiers(line: str) -> list[str]: ...
def _hash_pindatum(file_abspath: Path, pkg_name: str, qualifiers: list[str]) -> int: ...
@dataclass(**DC_SLOTS)
class PinDatum(Hashable):
    file_abspath: Path
    pkg_name: str
    line: str
    specifiers: list[str]
    qualifiers: list[str]

    def __hash__(self) -> int: ...
    def __eq__(self, right: object) -> bool: ...
    def __lt__(self, right: object) -> bool: ...

# public, not private TypeVar
DATUM = TypeVar("DATUM", bound=PinDatum)  # noqa: Y001
DatumByPkg: TypeAlias = dict[str, set[PinDatum]]

def pprint_pins(pins: Iterable[DATUM]) -> str: ...

class InFileType(enum.Enum):
    FILES = "_files"
    ZEROES = "_zeroes"

    def __eq__(self, other: object) -> bool: ...

class OutLastSuffix(enum.Enum):
    LOCK = SUFFIX_LOCKED
    UNLOCK = SUFFIX_UNLOCKED

    def __eq__(self, other: object) -> bool: ...

def in_generic(
    inst: object,
    val: Any,
    field_name: str = "file_abspath",
    set_name: InFileType | None = ...,
    is_abspath_ok: bool | None = False,
) -> bool: ...
