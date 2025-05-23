"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

wreck pytest conftest.py
"""

import re
import shutil
from collections.abc import Sequence
from pathlib import (
    Path,
    PurePath,
)
from typing import Any

import pytest

from wreck._run_cmd import run_cmd
from wreck._safe_path import resolve_path

from .wd_wrapper import WorkDir

pytest_plugins = [
    "logging_strict",
    "has_logging_occurred",
]


def pytest_addoption(parser: pytest.Parser):
    """Add cli options"""
    # parser.addoption("--nonloc", action="store_true", help="Include nonlocal tests")
    pass


class FileRegression:
    """Compare previous runs files.

    :ivar file_regression: file to compare against?
    :vartype file_regression: typing.Self

    .. todo:: when Sphinx<=6 is dropped

       Remove line starting with re.escape(" translation_progress=

    .. todo:: when Sphinx<7.2 is dropped

       Remove line starting with original_url=

    """

    ignores = (
        # Remove when support for Sphinx<=6 is dropped,
        re.escape(" translation_progress=\"{'total': 0, 'translated': 0}\""),
        # Remove when support for Sphinx<7.2 is dropped,
        r"original_uri=\"[^\"]*\"\s",
    )

    def __init__(self, file_regression: "FileRegression") -> None:
        """FileRegression constructor."""
        self.file_regression = file_regression

    def check(self, data: str, **kwargs: dict[str, Any]) -> str:
        """Check previous run against current run file.

        :param data: file contents
        :type data: str
        :param kwargs: keyword options are passed thru
        :type kwargs: dict[str, typing.Any]
        :returns: diff of file contents?
        :rtype: str
        """
        return self.file_regression.check(self._strip_ignores(data), **kwargs)

    def _strip_ignores(self, data: str) -> str:
        """Helper to strip ignores from data.

        :param data: file contents w/o ignore statements
        :type data: str
        :returns: sanitized file contents
        :rtype: str
        """
        cls = type(self)
        for ig in cls.ignores:
            data = re.sub(ig, "", data)
        return data


@pytest.fixture()
def file_regression(file_regression: "FileRegression") -> FileRegression:
    """Comparison files will need updating.

    .. seealso::

       Awaiting resolution of `pytest-regressions#32 <https://github.com/ESSS/pytest-regressions/issues/32>`_

    """
    return FileRegression(file_regression)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    attach each test's TestReport to the test Item so fixtures can
    decide how to finalize based on the test result.

    fixtures can access the TestReport from the `request` fixture at
    `request.node.test_report`.

    .. seealso::

       https://stackoverflow.com/a/70598731

    """
    test_report = (yield).get_result()
    if test_report.when == "call":
        item.test_report = test_report


@pytest.fixture()
def prepare_folders_files(request):
    """Prepare folders and files within folder."""

    set_folders = set()

    def _method(seq_rel_paths, tmp_path):
        """Creates folders and empty files

        :param seq_rel_paths: Relative file paths. Creates folders as well
        :type seq_rel_paths:

           collections.abc.Sequence[str | pathlib.Path] | collections.abc.MutableSet[str | pathlib.Path]

        :param tmp_path: Start absolute path
        :type tmp_path: pathlib.Path
        :returns: Set of absolute paths of created files
        :rtype: set[pathlib.Path]
        """
        set_abs_paths = set()
        is_seq = seq_rel_paths is not None and (
            (isinstance(seq_rel_paths, Sequence) and not isinstance(seq_rel_paths, str))
            or isinstance(seq_rel_paths, set)
        )
        if is_seq:
            for posix in seq_rel_paths:
                if isinstance(posix, str):
                    abs_path = tmp_path.joinpath(*posix.split("/"))
                elif issubclass(type(posix), PurePath):
                    if not posix.is_absolute():
                        abs_path = tmp_path / posix
                    else:  # pragma: no cover
                        # already absolute
                        abs_path = posix
                else:
                    abs_path = None

                if abs_path is not None:
                    set_abs_paths.add(abs_path)
                    set_folders.add(abs_path.parent)
                    abs_path.parent.mkdir(parents=True, exist_ok=True)
                    abs_path.touch()
        else:
            abs_path = None

        return set_abs_paths

    yield _method

    # cleanup
    if request.node.test_report.outcome == "passed":
        for abspath_folder in set_folders:
            shutil.rmtree(abspath_folder, ignore_errors=True)


@pytest.fixture()
def prep_pyproject_toml(request):
    """cli doesn't offer a ``parent_dir`` option to bypass ``--path``.
    Instead copy and rename the test ``pyproject.toml`` to the ``tmp_path``
    """
    lst_delete_me = []

    def _method(p_toml_file, path_dest_dir, rename="pyproject.toml"):
        """Copy and rename file. Does not necessarily have to be ``pyproject.toml``

        :param p_toml_file:

           Path to a ``pyproject.toml``. A copy will be made, original untouched

        :type p_toml_file: pathlib.Path
        :param path_dest_dir: destination tmp_path
        :type path_dest_dir: pathlib.Path
        :returns: Path to the copied and renamed file within it's new home, temp folder
        :rtype: pathlib.Path
        """
        if p_toml_file is not None and issubclass(type(p_toml_file), PurePath):
            # copy
            path_dest = path_dest_dir.joinpath(p_toml_file.name)
            shutil.copy(p_toml_file, path_dest_dir)
            # rename
            path_f = path_dest.parent.joinpath(rename)
            shutil.move(path_dest, path_f)
            ret = path_f
            lst_delete_me.append(path_f)
        else:
            ret = None

        return ret

    yield _method

    # cleanup
    if request.node.test_report.outcome == "passed":
        for path_delete_me in lst_delete_me:
            if (
                path_delete_me is not None
                and issubclass(type(path_delete_me), PurePath)
                and path_delete_me.exists()
                and path_delete_me.is_file()
            ):
                path_delete_me.unlink()


@pytest.fixture
def path_project_base():
    """Fixture to get project base folder"""

    def _method():
        """Get project base folder."""
        if "__pycache__" in __file__:
            # cached
            path_tests = Path(__file__).parent.parent
        else:
            # not cached
            path_tests = Path(__file__).parent
        path_cwd = path_tests.parent

        return path_cwd

    return _method


@pytest.fixture()
def wd(tmp_path: Path) -> WorkDir:
    """Create a workdir within tmp_path.

    In another fixture, add a package base folder.

    :param tmp_path: Temporary folder
    :type tmp_path: pathlib.Path
    :returns: WorkDir instance
    :rtype: .wd_wrapper.WorkDir

    .. seealso::

       Credit
       `[Author] <https://github.com/pypa/setuptools-scm/blob/main/pyproject.toml>`_
       `[Source] <https://github.com/pypa/setuptools_scm/blob/main/testing/conftest.py>`_
       `[License: MIT] <https://github.com/pypa/setuptools-scm/blob/main/LICENSE>`_

    """
    target_wd = tmp_path.resolve() / "wd"
    target_wd.mkdir()
    return WorkDir(target_wd)


@pytest.fixture
def verify_tag_version():
    """Fixture to verify version file contents."""

    def _method(cwd, sem_ver_str):
        """Verify version file contains a given semantic version str.

        :param cwd: package base folder
        :type cwd: pathlib.Path
        :param sem_ver_str: expected semantic version
        :type sem_ver_str: str
        :returns: True if versions match otherwise False
        :rtype: bool
        """
        cmd = [
            resolve_path("drain-swamp"),
            "tag",
        ]
        t_ret = run_cmd(cmd, cwd=cwd)
        out, err, exit_code, exc = t_ret
        is_eq = out == sem_ver_str

        return is_eq

    return _method
