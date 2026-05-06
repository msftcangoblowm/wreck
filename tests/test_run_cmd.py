"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Module _run_cmd encapsulates subprocess typical usage.

Unit test -- Module

.. code-block:: shell

   python -m coverage run --source='wreck._run_cmd' -m pytest \
   --showlocals tests/test_run_cmd.py && coverage report \
   --data-file=.coverage --include="**/_run_cmd.py"

"""

import os
import sys
from typing import TYPE_CHECKING

import pytest

from wreck._run_cmd import run_cmd
from wreck._safe_path import (
    is_win,
    resolve_path,
)
from wreck.constants import g_app_name

if TYPE_CHECKING:
    import logging
    from collections.abc import (
        Callable,
        MutableSet,
        Sequence,
    )
    from pathlib import Path
    from typing import Union


@pytest.mark.logging_package_name(g_app_name)
def test_run_cmd(
    tmp_path: "Path",
    prepare_folders_files: "Callable[[Union[Sequence[Union[str, Path]], MutableSet[Union[str, Path]]], Path], set[Path]]",
    logging_strict: "Callable[[], tuple[logging.Logger, Sequence[logging.Logger]]]",
) -> None:
    """Test run_cmd."""
    # pytest --showlocals --log-level INFO -k "test_run_cmd" tests
    t_two = logging_strict()
    logger, loggers = t_two

    # expecting Sequence
    cwd = tmp_path
    env = os.environ

    # cmd unsupported type
    invalids = (
        0.1234,
        None,
    )
    for invalid in invalids:
        with pytest.raises(TypeError):
            run_cmd(
                invalid,  # type: ignore[arg-type]
            )

        # executable path is incorrect. env --> None. cwd --> None
        cmd_0 = ("bin/true",)
        t_ret = run_cmd(
            cmd_0,
            env=invalid,  # type: ignore[arg-type]
            cwd=invalid,  # type: ignore[arg-type]
        )
        out, err, exit_code, str_exc = t_ret
        if is_win():
            expected_msg = """The system cannot find the file specified"""
        else:
            expected_msg = """No such file or directory"""
        if str_exc is not None:
            assert str_exc.startswith(expected_msg)

    # Something printed to stderr
    # prepare
    #    create CHANGES.rst
    seq_rel_paths = ("CHANGES.rst",)
    prepare_folders_files(seq_rel_paths, tmp_path)

    # act
    #    pygmentize installed from requirements/manage.in or requirements/dev.in
    #    pygmentize prints a list of lexers. So harmless
    pygmentize_optabspath = resolve_path("pygmentize")
    if pygmentize_optabspath is not None:
        cmd_1 = [pygmentize_optabspath, "-L"]
        t_ret = run_cmd(cmd_1, cwd=cwd)
        out, err, exit_code, str_exc = t_ret

        # verify
        assert exit_code == 0
        assert out is not None
        assert len(out.strip()) != 0

    # Something printed to stdout
    valids = (
        (sys.executable, "-V"),
        f"{sys.executable} -V",
    )
    for cmd_2 in valids:
        logger.info(f"cmd: {cmd_2!r}")

        t_ret = run_cmd(cmd_2, env=env)
        out, err, exit_code, str_exc = t_ret
        if exit_code != 0:
            logger.info(f"str_exc: {str_exc!r}")
            logger.info(f"err: {err!r}")
            logger.info(f"out: {out!r}")
        assert exit_code == 0
        assert out is not None
        assert len(out.strip()) != 0
