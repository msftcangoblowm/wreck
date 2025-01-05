"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Unit test -- Module

.. code-block:: shell

   python -m coverage run --source='wreck.lock_fixing' -m pytest \
   --showlocals tests/test_lock_fixing.py && coverage report \
   --data-file=.coverage --include="**/lock_fixing.py"

"""

import shutil
from collections.abc import Sequence  # noqa: F401
from pathlib import Path

import pytest
from logging_strict.tech_niques import get_locals  # noqa: F401

from wreck.constants import (
    SUFFIX_IN,
    SUFFIX_LOCKED,
    g_app_name,
)
from wreck.exceptions import MissingRequirementsFoldersFiles
from wreck.lock_fixing import (  # noqa: F401
    Fixing,
    _fix_resolvables,
    _load_once,
    fix_requirements_lock,
)
from wreck.lock_util import replace_suffixes_last
from wreck.pep518_venvs import VenvMapLoader

testdata_resolve_resolvable_conflicts = (
    (
        Path(__file__).parent.joinpath(
            "_unresolvable_conflict",
            "constraints-unresolvable.pyproject_toml",
        ),
        ".venv",
        (),
        (
            Path(__file__).parent.joinpath(
                "_unresolvable_conflict",
                "pip-lt.unlock",
            ),
            Path(__file__).parent.joinpath(
                "_unresolvable_conflict",
                "pip-lt.lock",
            ),
            Path(__file__).parent.joinpath(
                "_unresolvable_conflict",
                "pip-ge.unlock",
            ),
            Path(__file__).parent.joinpath(
                "_unresolvable_conflict",
                "pip-ge.lock",
            ),
        ),
        0,
        1,
    ),
    (
        Path(__file__).parent.joinpath(
            "_unsynced",
            "unsynced.pyproject_toml",
        ),
        ".venv",
        (),
        (
            Path(__file__).parent.joinpath(
                "_unsynced",
                "unsynced_0.unlock",
            ),
            Path(__file__).parent.joinpath(
                "_unsynced",
                "unsynced_0.lock",
            ),
            Path(__file__).parent.joinpath(
                "_unsynced",
                "unsynced_1.unlock",
            ),
            Path(__file__).parent.joinpath(
                "_unsynced",
                "unsynced_1.lock",
            ),
        ),
        1,
        0,
    ),
    (
        Path(__file__).parent.joinpath(
            "_transitive_conflict",
            "transitive.pyproject_toml",
        ),
        ".venv",
        (),
        (
            Path(__file__).parent.joinpath(
                "_transitive_conflict",
                "transitive_0.unlock",
            ),
            Path(__file__).parent.joinpath(
                "_transitive_conflict",
                "transitive_0.lock",
            ),
            Path(__file__).parent.joinpath(
                "_transitive_conflict",
                "transitive_1.unlock",
            ),
            Path(__file__).parent.joinpath(
                "_transitive_conflict",
                "transitive_1.lock",
            ),
        ),
        1,
        0,
    ),
    (
        Path(__file__).parent.joinpath(
            "_arbitrary_equality",
            "invalid_operator.pyproject_toml",
        ),
        ".venv",
        (),
        (
            Path(__file__).parent.joinpath(
                "_arbitrary_equality",
                "invalid_operator_0.unlock",
            ),
            Path(__file__).parent.joinpath(
                "_arbitrary_equality",
                "invalid_operator_0.lock",
            ),
            Path(__file__).parent.joinpath(
                "_arbitrary_equality",
                "invalid_operator_1.unlock",
            ),
            Path(__file__).parent.joinpath(
                "_arbitrary_equality",
                "invalid_operator_1.lock",
            ),
        ),
        0,
        1,
    ),
    (
        Path(__file__).parent.joinpath(
            "_too_many_specifiers",
            "too_many_specifiers.pyproject_toml",
        ),
        ".venv",
        (),
        (
            Path(__file__).parent.joinpath(
                "_too_many_specifiers",
                "too_many_specifiers_0.unlock",
            ),
            Path(__file__).parent.joinpath(
                "_too_many_specifiers",
                "too_many_specifiers_0.lock",
            ),
            Path(__file__).parent.joinpath(
                "_too_many_specifiers",
                "too_many_specifiers_1.unlock",
            ),
            Path(__file__).parent.joinpath(
                "_too_many_specifiers",
                "too_many_specifiers_1.lock",
            ),
        ),
        0,
        1,
    ),
    (
        Path(__file__).parent.joinpath(
            "_invalid_specifier",
            "invalid_specifier.pyproject_toml",
        ),
        ".venv",
        (),
        (
            Path(__file__).parent.joinpath(
                "_invalid_specifier",
                "invalid_specifier_0.unlock",
            ),
            Path(__file__).parent.joinpath(
                "_invalid_specifier",
                "invalid_specifier_0.lock",
            ),
            Path(__file__).parent.joinpath(
                "_invalid_specifier",
                "invalid_specifier_1.unlock",
            ),
            Path(__file__).parent.joinpath(
                "_invalid_specifier",
                "invalid_specifier_1.lock",
            ),
        ),
        1,
        0,
    ),
)
ids_resolve_resolvable_conflicts = (
    "pip ge 24.2 pip lt 24.2 unresolvable conflict",
    "unsynced lock files bring into sync",
    "no package in .in conflict in .lock",
    "invalid operator arbitrary equality",
    "too many specifiers more than 2",
    "invalid specifier found, line is ignored. No warning",
)


@pytest.mark.logging_package_name(g_app_name)
@pytest.mark.parametrize(
    (
        "path_pyproject_toml, venv_path, base_relpaths, "
        "to_requirements_dir, expected_resolvable_count, "
        "expected_unresolvable_count"
    ),
    testdata_resolve_resolvable_conflicts,
    ids=ids_resolve_resolvable_conflicts,
)
def test_locks_before_fix(
    path_pyproject_toml,
    venv_path,
    base_relpaths,
    to_requirements_dir,
    expected_resolvable_count,
    expected_unresolvable_count,
    tmp_path,
    prepare_folders_files,
    prep_pyproject_toml,
    logging_strict,
):
    """Fix .locks only."""
    # pytest -vv --showlocals --log-level INFO -k "test_locks_before_fix" tests
    # pytest -vv --showlocals --log-level INFO tests/test_lock_fixing.py::test_locks_before_fix[unsynced\ lock\ files\ bring\ into\ sync]
    # pytest -vv --showlocals --log-level INFO tests/test_lock_fixing.py::test_locks_before_fix[invalid\ specifier\ found]
    t_two = logging_strict()
    logger, loggers = t_two

    # prepare
    #    pyproject.toml
    path_dest_pyproject_toml = prep_pyproject_toml(path_pyproject_toml, tmp_path)
    loader = VenvMapLoader(path_dest_pyproject_toml.as_posix())

    # Verify -- missing venv folder --> NotADirectoryError
    with pytest.raises(NotADirectoryError):
        Fixing(loader, venv_path)

    # prepare
    #    venv_path folder. To avoid NotADirectoryError
    prep_these = (".venv/.python-version",)
    prepare_folders_files(prep_these, tmp_path)

    # Verify -- expecting Path or str
    invalids = (
        None,
        1.234,
    )
    for invalid in invalids:
        with pytest.raises(TypeError):
            Fixing(loader, invalid)

    # Verify -- missing transitive/support files and folders
    with pytest.raises(MissingRequirementsFoldersFiles):
        Fixing(loader, venv_path)

    # prepare -- requirements folder
    prep_these = ("requirements/junk.deleteme",)
    prepare_folders_files(prep_these, tmp_path)

    #   Copy empties
    prep_these = []
    for suffix in (SUFFIX_IN, SUFFIX_LOCKED):
        for base_relpath in base_relpaths:
            prep_these.append(f"{base_relpath}{suffix}")
        prepare_folders_files(prep_these, tmp_path)

    #    Copy real .unlock --> .in files
    for abspath_src in to_requirements_dir:
        if abspath_src.suffix == ".unlock":
            src_abspath = str(abspath_src)
            abspath_dest = tmp_path / "requirements" / abspath_src.name
            abspath_dest_in = replace_suffixes_last(abspath_dest, SUFFIX_IN)
            shutil.copy(src_abspath, abspath_dest_in)

    #    Copy real .lock files
    for abspath_src in to_requirements_dir:
        if abspath_src.suffix == ".lock":
            src_abspath = str(abspath_src)
            abspath_dest = tmp_path / "requirements" / abspath_src.name
            shutil.copy(src_abspath, abspath_dest)

    # Act
    fixing = Fixing(loader, venv_path)

    #    for debugging
    ins = fixing._ins  # noqa: F841
    locks = fixing._locks  # noqa: F841

    fixing.get_issues()
    lst_resolvables = fixing.resolvables
    lst_unresolvables = fixing.unresolvables

    func_path = f"{g_app_name}.lock_fixing._load_once"
    args = (fixing._ins, fixing._locks, fixing._venv_relpath)
    kwargs = {}
    t_ret = get_locals(func_path, _load_once, *args, **kwargs)  # noqa: F841
    assert isinstance(t_ret, Sequence)
    assert len(t_ret) == 2
    t_out, t_locals = t_ret

    actual_unresolvables_count = len(lst_unresolvables)
    actual_resolvables_count = len(lst_resolvables)
    # Verify -- resolvables and unresolvables expected count
    assert actual_resolvables_count == expected_resolvable_count
    assert actual_unresolvables_count == expected_unresolvable_count

    # act -- fix .lock files
    fixing.fix_resolvables(is_dry_run=None)
    msgs_issue = fixing.fixed_issues
    msgs_shared = fixing.resolvable_shared
    msgs_issue_count = len(msgs_issue)  # noqa: F841
    # assert actual_resolvables_count == msgs_issue_count
    msgs_shared_count = len(msgs_shared)

    # Verify -- .shared.in count
    #    Shared between venv, so not possible to fix automatically
    assert msgs_shared_count == 0

    # Call underlying function with specific kwargs
    _fix_resolvables(
        fixing._resolvables,
        fixing._locks,
        fixing._venv_relpath,
        is_dry_run=True,
        suffixes=None,
    )


@pytest.mark.logging_package_name(g_app_name)
@pytest.mark.parametrize(
    (
        "path_pyproject_toml, venv_path, base_relpaths, "
        "to_requirements_dir, expected_resolvable_count, "
        "expected_unresolvable_count"
    ),
    testdata_resolve_resolvable_conflicts,
    ids=ids_resolve_resolvable_conflicts,
)
def test_fix_requirements_lock(
    path_pyproject_toml,
    venv_path,
    base_relpaths,
    to_requirements_dir,
    expected_resolvable_count,
    expected_unresolvable_count,
    tmp_path,
    prepare_folders_files,
    prep_pyproject_toml,
    logging_strict,
):
    """Test fix_requirements_lock"""
    # pytest -vv --showlocals --log-level INFO -k "test_fix_requirements_lock" tests
    t_two = logging_strict()
    logger, loggers = t_two

    # prepare
    #    pyproject.toml
    path_dest_pyproject_toml = prep_pyproject_toml(path_pyproject_toml, tmp_path)
    loader = VenvMapLoader(path_dest_pyproject_toml.as_posix())

    # Verify -- missing venv base folder --> NotADirectoryError
    with pytest.raises(NotADirectoryError):
        fix_requirements_lock(loader, venv_path, is_dry_run=1.234)
        Fixing(loader, venv_path)

    # prepare -- venv_path folder
    prep_these = (".venv/.python-version",)
    prepare_folders_files(prep_these, tmp_path)

    # Verify -- arg venv_path unsupported type --> TypeError
    invalids = (
        None,
        1.234,
    )
    for invalid in invalids:
        with pytest.raises(TypeError):
            fix_requirements_lock(loader, invalid, is_dry_run=None)

    # Verify -- missing transitive/support files and folders
    with pytest.raises(MissingRequirementsFoldersFiles):
        fix_requirements_lock(loader, venv_path, is_dry_run=True)

    # prepare
    #    transitive/support file folders
    prep_these = ("requirements/junk.deleteme",)
    prepare_folders_files(prep_these, tmp_path)

    #   Copy empties
    prep_these = []
    for suffix in (SUFFIX_IN, SUFFIX_LOCKED):
        for base_relpath in base_relpaths:
            prep_these.append(f"{base_relpath}{suffix}")
        prepare_folders_files(prep_these, tmp_path)

    #    Copy real .unlock --> .in files
    for abspath_src in to_requirements_dir:
        if abspath_src.suffix == ".unlock":
            src_abspath = str(abspath_src)
            abspath_dest = tmp_path / "requirements" / abspath_src.name
            abspath_dest_in = replace_suffixes_last(abspath_dest, SUFFIX_IN)
            shutil.copy(src_abspath, abspath_dest_in)

    #    Copy real .lock files
    for abspath_src in to_requirements_dir:
        if abspath_src.suffix == ".lock":
            src_abspath = str(abspath_src)
            abspath_dest = tmp_path / "requirements" / abspath_src.name
            shutil.copy(src_abspath, abspath_dest)

    # act
    t_ret = fix_requirements_lock(loader, venv_path)
    msgs_fixed, lst_unresolvables, msgs_shared = t_ret

    # verify
    assert isinstance(msgs_fixed, list)
    assert isinstance(lst_unresolvables, list)
    assert isinstance(msgs_shared, list)
