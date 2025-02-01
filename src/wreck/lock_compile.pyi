from collections.abc import Generator
from pathlib import Path
from typing import Any

from .pep518_venvs import VenvMapLoader

def prepare_pairs(t_ins: tuple[Path]) -> Generator[tuple[str, str], None, None]: ...
def _postprocess_abspath_to_relpath(path_out: Path, path_parent: Path) -> None: ...
def _compile_one(
    in_abspath: str,
    lock_abspath: str,
    ep_path: str,
    path_cwd: Path,
    venv_relpath: str,
    timeout: Any = 15,
) -> tuple[Path | None, None | str]: ...
def _empty_in_empty_out(in_abspath: str, lock_abspath: str) -> bool: ...
def lock_compile(
    loader: VenvMapLoader,
    venv_relpath: str,
    timeout: Any = 15,
) -> tuple[tuple[str, ...], tuple[str, ...]]: ...
def is_timeout(failures: tuple[str, ...]) -> bool: ...
