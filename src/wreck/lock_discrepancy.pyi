import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from .lock_datum import (
    DatumByPkg,
    PinDatum,
)

if sys.version_info >= (3, 10):  # pragma: no cover py-gte-310-else
    from typing import TypeAlias
else:  # pragma: no cover py-gte-310
    from typing_extensions import TypeAlias

__all__ = (
    "PkgsWithIssues",
    "Resolvable",
    "ResolvedMsg",
    "UnResolvable",
    "filter_acceptable",
    "get_ss_set",
    "has_discrepancies_version",
    "get_the_fixes",
    "write_to_file_nudge_pin",
)

DC_SLOTS: dict[str, bool]
is_module_debug: Final[bool]
_logger: Final[logging.Logger]

PkgsWithIssues: TypeAlias = dict[str, dict[str, Version | set[Version]]]

def has_discrepancies_version(d_by_pkg: DatumByPkg) -> PkgsWithIssues: ...
def get_ss_set(set_pindatum: set[PinDatum]) -> set[SpecifierSet]: ...
def _get_specifiers(set_pindatum: set[PinDatum]) -> list[PinDatum]: ...
def _parse_specifiers(specifiers: list[str]) -> str | None: ...
def nudge_pin_unlock_v1(str_operator: str, found: Version) -> str: ...
def nudge_pin_lock_v1(found: Version) -> str: ...
def filter_acceptable(
    set_pindatum: set[PinDatum],
    ss_set: set[SpecifierSet],
    highest: Version,
    others: set[Version],
) -> tuple[set[SpecifierSet], list[list[str]], Version | None]: ...
def get_compatible_release(
    highest: Version,
    lsts_specifiers: list[list[str]],
) -> tuple[str, str, bool]: ...
def get_the_fixes(
    set_acceptable: set[SpecifierSet],
    lsts_specifiers: list[list[str]],
    highest: Version,
    is_eq_affinity_value: Version | None,
    is_ss_count_zero: bool,
) -> tuple[str, str, bool]: ...
@dataclass(**DC_SLOTS)
class Resolvable:
    venv_path: str | Path
    pkg_name: str
    qualifiers: str
    nudge_unlock: str
    nudge_lock: str

@dataclass(**DC_SLOTS)
class UnResolvable:
    venv_path: str
    pkg_name: str
    qualifiers: str
    sss: set[SpecifierSet]
    v_highest: Version
    v_others: set[Version]
    pins: set[PinDatum]

@dataclass(**DC_SLOTS)
class ResolvedMsg:
    abspath_f: Path
    nudge_pin_line: str

def extract_full_package_name(
    line: str,
    pkg_name_desired: str,
) -> str | None: ...
def write_to_file_nudge_pin(
    path_f: Path,
    pkg_name: str,
    nudge_pin_line: str,
) -> None: ...
