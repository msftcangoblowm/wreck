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
g_logger_dotted_path: Final[str]
_logger: logging.Logger

help_path: Final[str]
help_venv_path: Final[str]
help_timeout: Final[str]
help_is_dry_run: Final[str]
help_show_unresolvables: Final[str]
help_show_fixed: Final[str]
help_show_resolvable_shared: Final[str]
help_verbose: Final[str]

EPILOG_FIX_V2: Final[str]
EPILOG_UNLOCK: Final[str]

def present_results(
    fcn: Callable[[str, dict[str, bool]], None],
    venv_relpath: str,
    lock_msgs_for_venv: list[ResolvedMsg],
    lock_unresolvables_for_venv: list[UnResolvable],
    lock_applies_to_shared_for_venv: list[tuple[str, Resolvable, PinDatum]],
    unlock_msgs_for_venv: list[ResolvedMsg],
    unlock_applies_to_shared_for_venv: list[tuple[str, Resolvable, PinDatum]],
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
