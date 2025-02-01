import logging
from collections.abc import Callable
from pathlib import Path
from typing import Final

from .lock_datum import PinDatum
from .lock_discrepancy import (
    Resolvable,
    ResolvedMsg,
    UnResolvable,
)

entrypoint_name: Final[str]

is_module_debug: Final[bool]
_logger: logging.Logger

help_path: Final[str]
help_venv_path: Final[str]
help_timeout: Final[str]
help_is_dry_run: Final[str]
help_show_unresolvables: Final[str]
help_show_fixed: Final[str]
help_show_resolvable_shared: Final[str]

EPILOG_LOCK: Final[str]
EPILOG_UNLOCK: Final[str]
EPILOG_REQUIREMENTS_FIX: Final[str]

def present_results(
    fcn: Callable[[str, dict[str, bool]], None],
    venv_relpath: str,
    msgs_for_venv: list[ResolvedMsg],
    unresolvables_for_venv: list[UnResolvable],
    applies_to_shared_for_venv: list[tuple[str, Resolvable, PinDatum]],
    show_unresolvables: bool,
    show_fixed: bool,
    show_resolvable_shared: bool,
) -> None: ...
def main() -> None: ...
def requirements_fix_v2(
    path: Path,
    venv_relpath: str,
    timeout: int,
    show_unresolvables: bool,
    show_fixed: bool,
    show_resolvable_shared: bool,
) -> None: ...
def requirements_unlock(
    path: Path,
    venv_relpath: str,
) -> None: ...
def requirements_fix_v1(
    path: Path,
    venv_relpath: str,
    is_dry_run: bool,
    show_unresolvables: bool,
    show_fixed: bool,
    show_resolvable_shared: bool,
) -> None: ...
