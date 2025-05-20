import logging
from collections.abc import Sequence
from typing import (
    Any,
    Final,
)

from .lock_collections import Ins
from .lock_datum import (
    DatumByPkg,
    OutLastSuffix,
    PinDatum,
)
from .lock_discrepancy import (
    Resolvable,
    ResolvedMsg,
    UnResolvable,
)
from .pep518_venvs import VenvMapLoader

__all__ = ("Fixing",)
is_module_debug: Final[bool]
_logger: Final[logging.Logger]

class OutMessages:
    __slots__ = (
        "_last_suffix",
        "_unresolvables",
        "_fixed_issues",
        "_resolvable_shared",
    )

    def __init__(self, last_suffix: OutLastSuffix) -> None: ...
    def append(self, item: Any, last_suffix: OutLastSuffix = ...) -> None: ...
    def extend(self, items: Any, last_suffix: OutLastSuffix = ...) -> None: ...
    @property
    def resolvable_shared(self) -> list[tuple[str, Resolvable, PinDatum]]: ...
    @property
    def unresolvables(self) -> list[UnResolvable]: ...
    @property
    def fixed_issues(self) -> list[ResolvedMsg]: ...

def _check_is_dry_run(is_dry_run: Any, default: bool = False) -> bool: ...
def _get_qualifiers(d_subset: DatumByPkg) -> dict[str, str]: ...
def _load_once(
    ins: Ins,
    locks: Ins,
    venv_relpath: str,
) -> tuple[list[Resolvable], list[UnResolvable]]: ...
def _fix_resolvables(
    resolvables: Sequence[Resolvable],
    locks: Ins,
    venv_relpath: str,
    is_dry_run: bool | None = False,
    suffixes: tuple[str, ...] = ...,
) -> tuple[list[ResolvedMsg], list[tuple[str, str, Resolvable, PinDatum]]]: ...

class Fixing:
    _ins: Ins
    _locks: Ins
    _venv_relpath: str
    _loader: VenvMapLoader
    _out_lock_messages: OutMessages
    _out_unlock_messages: OutMessages

    def __init__(
        self,
        loader: VenvMapLoader,
        venv_relpath: str,
        out_lock_messages: OutMessages,
        out_unlock_messages: OutMessages,
    ) -> None: ...
    @staticmethod
    def fix_requirements_lock(
        loader: VenvMapLoader,
        venv_relpath: str,
        is_dry_run: Any | None = False,
    ) -> Fixing: ...
    def fix_unlock(self, is_dry_run: Any | None = False) -> None: ...
    def get_issues(self) -> None: ...
    def fix_resolvables(self, is_dry_run: Any | None = False) -> None: ...
    @property
    def resolvables(self) -> list[Resolvable]: ...
