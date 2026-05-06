"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Unit test -- Module

.. code-block:: shell

   python -m coverage run --source='wreck.lock_fixing' -m pytest \
   --showlocals tests/test_lock_fixing.py && coverage report \
   --data-file=.coverage --include="**/lock_fixing.py"

"""

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from logging_strict.tech_niques import get_locals_dynamic  # noqa: F401
from packaging.version import Version

from wreck.constants import (
    SUFFIX_IN,
    SUFFIX_LOCKED,
    g_app_name,
)
from wreck.exceptions import MissingRequirementsFoldersFiles
from wreck.lock_datum import (
    OutLastSuffix,
    PinDatum,
)
from wreck.lock_discrepancy import (
    Resolvable,
    ResolvedMsg,
    UnResolvable,
)
from wreck.lock_fixing import (  # noqa: F401
    Fixing,
    OutMessages,
    _fix_resolvables,
    _load_once,
)
from wreck.lock_util import replace_suffixes_last
from wreck.pep518_venvs import VenvMapLoader

if TYPE_CHECKING:
    import logging
    from collections.abc import (
        Callable,
        MutableSet,
        Sequence,
    )
    from typing import Union

testdata_resolve_resolvable_conflicts = (
    (
        Path("_unresolvable_conflict").joinpath(
            "constraints-unresolvable.pyproject_toml"
        ),
        ".venv",
        (),
        (
            Path("_unresolvable_conflict").joinpath("pip-lt.unlock"),
            Path("_unresolvable_conflict").joinpath("pip-lt.lock"),
            Path("_unresolvable_conflict").joinpath("pip-ge.unlock"),
            Path("_unresolvable_conflict").joinpath("pip-ge.lock"),
        ),
        0,
        1,
    ),
    (
        Path("_unsynced").joinpath("unsynced.pyproject_toml"),
        ".venv",
        (),
        (
            Path("_unsynced").joinpath("unsynced_0.unlock"),
            Path("_unsynced").joinpath("unsynced_0.lock"),
            Path("_unsynced").joinpath("unsynced_1.unlock"),
            Path("_unsynced").joinpath("unsynced_1.lock"),
        ),
        1,
        0,
    ),
    (
        Path("_transitive_conflict").joinpath("transitive.pyproject_toml"),
        ".venv",
        (),
        (
            Path("_transitive_conflict").joinpath("transitive_0.unlock"),
            Path("_transitive_conflict").joinpath("transitive_0.lock"),
            Path("_transitive_conflict").joinpath("transitive_1.unlock"),
            Path("_transitive_conflict").joinpath("transitive_1.lock"),
        ),
        1,
        0,
    ),
    (
        Path("_arbitrary_equality").joinpath("invalid_operator.pyproject_toml"),
        ".venv",
        (),
        (
            Path("_arbitrary_equality").joinpath("invalid_operator_0.unlock"),
            Path("_arbitrary_equality").joinpath("invalid_operator_0.lock"),
            Path("_arbitrary_equality").joinpath("invalid_operator_1.unlock"),
            Path("_arbitrary_equality").joinpath("invalid_operator_1.lock"),
        ),
        0,
        1,
    ),
    (
        Path("_too_many_specifiers").joinpath("too_many_specifiers.pyproject_toml"),
        ".venv",
        (),
        (
            Path("_too_many_specifiers").joinpath("too_many_specifiers_0.unlock"),
            Path("_too_many_specifiers").joinpath("too_many_specifiers_0.lock"),
            Path("_too_many_specifiers").joinpath("too_many_specifiers_1.unlock"),
            Path("_too_many_specifiers").joinpath("too_many_specifiers_1.lock"),
        ),
        0,
        1,
    ),
    (
        Path("_invalid_specifier").joinpath("invalid_specifier.pyproject_toml"),
        ".venv",
        (),
        (
            Path("_invalid_specifier").joinpath("invalid_specifier_0.unlock"),
            Path("_invalid_specifier").joinpath("invalid_specifier_0.lock"),
            Path("_invalid_specifier").joinpath("invalid_specifier_1.unlock"),
            Path("_invalid_specifier").joinpath("invalid_specifier_1.lock"),
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
        "relpath_pyproject_toml, venv_path, base_relpaths, "
        "to_requirements_dir, expected_resolvable_count, "
        "expected_unresolvable_count"
    ),
    testdata_resolve_resolvable_conflicts,
    ids=ids_resolve_resolvable_conflicts,
)
def test_locks_before_fix(
    relpath_pyproject_toml: "Path",
    venv_path: str,
    base_relpaths: tuple[str, ...],
    to_requirements_dir: "Sequence[Path]",
    expected_resolvable_count: int,
    expected_unresolvable_count: int,
    request: "pytest.FixtureRequest",
    tmp_path: "Path",
    prepare_folders_files: "Callable[[Union[Sequence[Union[str, Path]], MutableSet[Union[str, Path]]], Path], set[Path]]",
    prep_pyproject_toml: "Callable[[Path, Path, Union[Path, str, None]], Path]",
    logging_strict: "Callable[[], tuple[logging.Logger, Sequence[logging.Logger]]]",
) -> None:
    """Fix .locks only."""
    # pytest -vv --showlocals --log-level INFO -k "test_locks_before_fix" tests
    # pytest -vv --showlocals --log-level INFO tests/test_lock_fixing.py::test_locks_before_fix[unsynced\ lock\ files\ bring\ into\ sync]
    # pytest -vv --showlocals --log-level INFO tests/test_lock_fixing.py::test_locks_before_fix[invalid\ specifier\ found]
    abspath_tests_dir = request.path.parent
    path_pyproject_toml = abspath_tests_dir.joinpath(relpath_pyproject_toml)
    t_two = logging_strict()
    logger, loggers = t_two

    # prepare
    #    pyproject.toml
    path_dest_pyproject_toml = prep_pyproject_toml(path_pyproject_toml, tmp_path, None)
    loader = VenvMapLoader(path_dest_pyproject_toml.as_posix())

    #    has-a feature normally provided by factory Fixing.fix_requirements_lock
    lock_msgs = OutMessages(last_suffix=OutLastSuffix.LOCK)
    unlock_msgs = OutMessages(last_suffix=OutLastSuffix.UNLOCK)

    # Verify -- missing venv folder --> NotADirectoryError
    with pytest.raises(NotADirectoryError):
        Fixing(loader, venv_path, lock_msgs, unlock_msgs)

    # prepare
    #    venv_path folder. To avoid NotADirectoryError
    prep_these = [".venv/.python-version"]
    prepare_folders_files(prep_these, tmp_path)

    # Verify -- expecting Path or str
    invalids = (
        None,
        1.234,
    )
    for invalid in invalids:
        with pytest.raises(TypeError):
            Fixing(
                loader,
                invalid,  # type: ignore[arg-type]
                lock_msgs,
                unlock_msgs,
            )

    # Verify -- missing transitive/support files and folders
    with pytest.raises(MissingRequirementsFoldersFiles):
        Fixing(loader, venv_path, lock_msgs, unlock_msgs)

    # prepare -- requirements folder
    prep_these = ["requirements/junk.deleteme"]
    prepare_folders_files(prep_these, tmp_path)

    #   Copy empties
    prep_these = []
    for suffix in (SUFFIX_IN, SUFFIX_LOCKED):
        for base_relpath in base_relpaths:
            prep_these.append(f"{base_relpath}{suffix}")
        prepare_folders_files(prep_these, tmp_path)

    #    Copy real .unlock --> .in files
    for relpath_src in to_requirements_dir:
        abspath_src = abspath_tests_dir.joinpath(relpath_src)
        if abspath_src.suffix == ".unlock":
            abspath_dest = tmp_path / "requirements" / abspath_src.name
            abspath_dest_in = replace_suffixes_last(abspath_dest, SUFFIX_IN)
            shutil.copy(abspath_src.as_posix(), abspath_dest_in.as_posix())

    #    Copy real .lock files
    for relpath_src in to_requirements_dir:
        abspath_src = abspath_tests_dir.joinpath(relpath_src)
        if abspath_src.suffix == ".lock":
            abspath_dest = tmp_path / "requirements" / abspath_src.name
            shutil.copy(abspath_src.as_posix(), abspath_dest.as_posix())

    # Act
    fixing = Fixing(loader, venv_path, lock_msgs, unlock_msgs)

    #    for debugging
    ins = fixing._ins  # noqa: F841
    locks = fixing._locks  # noqa: F841

    fixing.get_issues()
    lst_resolvables = fixing.resolvables
    lst_unresolvables = fixing._out_lock_messages.unresolvables

    """
    args = (fixing._ins, fixing._locks, fixing._venv_relpath)
    kwargs = {}
    t_ret = get_locals_dynamic(_load_once, *args, **kwargs)  # noqa: F841
    assert isinstance(t_ret, Sequence)
    assert len(t_ret) == 2
    t_out, t_locals = t_ret
    """

    actual_unresolvables_count = len(lst_unresolvables)
    actual_resolvables_count = len(lst_resolvables)
    # Verify -- resolvables and unresolvables expected count
    assert actual_resolvables_count == expected_resolvable_count
    assert actual_unresolvables_count == expected_unresolvable_count

    # act -- fix .lock files
    fixing.fix_resolvables(is_dry_run=None)
    msgs_issue = fixing._out_lock_messages.fixed_issues
    msgs_shared = fixing._out_lock_messages.resolvable_shared
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
        suffixes=None,  # type: ignore[arg-type]
    )


@pytest.mark.logging_package_name(g_app_name)
@pytest.mark.parametrize(
    (
        "relpath_pyproject_toml, venv_path, base_relpaths, "
        "to_requirements_dir, expected_resolvable_count, "
        "expected_unresolvable_count"
    ),
    testdata_resolve_resolvable_conflicts,
    ids=ids_resolve_resolvable_conflicts,
)
def test_fix_requirements_lock(
    relpath_pyproject_toml: "Path",
    venv_path: str,
    base_relpaths: tuple[str, ...],
    to_requirements_dir: "Sequence[Path]",
    expected_resolvable_count: int,
    expected_unresolvable_count: int,
    request: "pytest.FixtureRequest",
    tmp_path: "Path",
    prepare_folders_files: "Callable[[Union[Sequence[Union[str, Path]], MutableSet[Union[str, Path]]], Path], set[Path]]",
    prep_pyproject_toml: "Callable[[Path, Path, Union[Path, str, None]], Path]",
    logging_strict: "Callable[[], tuple[logging.Logger, Sequence[logging.Logger]]]",
) -> None:
    """Test fix_requirements_lock"""
    # pytest -vv --showlocals --log-level INFO -k "test_fix_requirements_lock" tests
    abspath_tests_dir = request.path.parent
    path_pyproject_toml = abspath_tests_dir.joinpath(relpath_pyproject_toml)
    t_two = logging_strict()
    logger, loggers = t_two

    # prepare
    #    pyproject.toml
    path_dest_pyproject_toml = prep_pyproject_toml(
        path_pyproject_toml,
        tmp_path,
        None,
    )
    loader = VenvMapLoader(path_dest_pyproject_toml.as_posix())

    # Verify -- missing venv base folder --> NotADirectoryError
    with pytest.raises(NotADirectoryError):
        Fixing.fix_requirements_lock(loader, venv_path, is_dry_run=1.234)

    # prepare -- venv_path folder
    prep_these = [".venv/.python-version"]
    prepare_folders_files(prep_these, tmp_path)

    # Verify -- arg venv_path unsupported type --> TypeError
    invalids = (
        None,
        1.234,
    )
    for invalid in invalids:
        with pytest.raises(TypeError):
            Fixing.fix_requirements_lock(
                loader,
                invalid,  # type: ignore[arg-type]
                is_dry_run=None,
            )

    # Verify -- missing transitive/support files and folders
    with pytest.raises(MissingRequirementsFoldersFiles):
        Fixing.fix_requirements_lock(loader, venv_path, is_dry_run=True)

    # prepare
    #    transitive/support file folders
    prep_these = ["requirements/junk.deleteme"]
    prepare_folders_files(prep_these, tmp_path)

    #   Copy empties
    prep_these = []
    for suffix in (SUFFIX_IN, SUFFIX_LOCKED):
        for base_relpath in base_relpaths:
            prep_these.append(f"{base_relpath}{suffix}")
        prepare_folders_files(prep_these, tmp_path)

    #    Copy real .unlock --> .in files
    for relpath_src in to_requirements_dir:
        abspath_src = abspath_tests_dir.joinpath(relpath_src)
        if abspath_src.suffix == ".unlock":
            abspath_dest = tmp_path / "requirements" / abspath_src.name
            abspath_dest_in = replace_suffixes_last(abspath_dest, SUFFIX_IN)
            shutil.copy(abspath_src.as_posix(), abspath_dest_in)

    #    Copy real .lock files
    for relpath_src in to_requirements_dir:
        abspath_src = abspath_tests_dir.joinpath(relpath_src)
        if abspath_src.suffix == ".lock":
            abspath_dest = tmp_path / "requirements" / abspath_src.name
            shutil.copy(abspath_src.as_posix(), abspath_dest.as_posix())

    # act
    fixing = Fixing.fix_requirements_lock(loader, venv_path)
    msgs_fixed = fixing._out_lock_messages.fixed_issues
    lst_unresolvables = fixing._out_lock_messages.unresolvables
    msgs_shared = fixing._out_lock_messages.resolvable_shared

    # verify
    assert isinstance(msgs_fixed, list)
    assert isinstance(lst_unresolvables, list)
    assert isinstance(msgs_shared, list)


testdata_outmessages = (
    (
        OutLastSuffix.LOCK,
        OutLastSuffix.LOCK,
        UnResolvable(".venv", "pip", "", set(), Version("24.2"), set(), set()),
    ),
    (
        OutLastSuffix.LOCK,
        OutLastSuffix.LOCK,
        (
            SUFFIX_LOCKED,
            Resolvable(
                ".venv", "pip", '; python_version <= "3.10"', "pip>=24.2", "pip>=24.3"
            ),
            PinDatum(
                Path(__file__).parent.joinpath(
                    "_qualifier_conflicts",
                    "qualifier_1.unlock",
                ),
                "pip",
                '"pip>=24.2',
                [">=24.2"],
                [],
            ),
        ),
    ),
    (
        OutLastSuffix.LOCK,
        OutLastSuffix.LOCK,
        ResolvedMsg(
            ".venv",
            Path(__file__).parent.joinpath(
                "_qualifier_conflicts",
                "qualifier_1.unlock",
            ),
            '"pip>=24.2',
        ),
    ),
    (
        OutLastSuffix.LOCK,
        None,
        UnResolvable(".venv", "pip", "", set(), Version("24.2"), set(), set()),
    ),
    (
        OutLastSuffix.LOCK,
        OutLastSuffix.LOCK,
        None,
    ),
    (
        OutLastSuffix.LOCK,
        OutLastSuffix.LOCK,
        1.1234,
    ),
)
ids_outmessages = (
    "UnResolvable LOCK",
    "tuple LOCK",
    "ResolvedMsg LOCK",
    "UnResolvable LOCK append type None",
    "msg is None",
    "non-None unsupported item type",
)


@pytest.mark.parametrize(
    "last_suffix, append_a_last_suffix, item",
    testdata_outmessages,
    ids=ids_outmessages,
)
def test_outmessages(
    last_suffix: "OutLastSuffix",
    append_a_last_suffix: "Union[OutLastSuffix, None]",
    item: "Union[float, None, ResolvedMsg, UnResolvable, tuple[str, Resolvable, PinDatum]]",
) -> None:
    """Exercise OutMessages"""
    # pytest -vv --showlocals --log-level INFO -k "test_outmessages" tests
    out_msgs = OutMessages(last_suffix)
    out_msgs.append(
        item,
        last_suffix=append_a_last_suffix,
    )
    assert isinstance(out_msgs.resolvable_shared, list)
    assert isinstance(out_msgs.unresolvables, list)
    assert isinstance(out_msgs.fixed_issues, list)


testdata_check_in_includes_lock = (
    (
        Path("_warn_include_lock").joinpath("prod_and_dev.pyproject_toml"),
        ".venv",
        (
            Path("_warn_include_lock").joinpath("dev.in"),
            Path("_warn_include_lock").joinpath("prod.in"),
            Path("_warn_include_lock").joinpath("dev.lock"),
            Path("_warn_include_lock").joinpath("prod.lock"),
        ),
        1,
    ),
)
ids_check_in_includes_lock = ("An .in file includes constraint to .lock file",)


@pytest.mark.parametrize(
    "relpath_pyproject_toml, venv_path, to_requirements_dir, msgs_count_expected",
    testdata_check_in_includes_lock,
    ids=ids_check_in_includes_lock,
)
def test_check_in_includes_lock(
    relpath_pyproject_toml: "Path",
    venv_path: str,
    to_requirements_dir: "Sequence[Path]",
    msgs_count_expected: int,
    request: "pytest.FixtureRequest",
    tmp_path: "Path",
    prep_pyproject_toml: "Callable[[Path, Path, Union[Path, str, None]], Path]",
    prepare_folders_files: "Callable[[Union[Sequence[Union[str, Path]], MutableSet[Union[str, Path]]], Path], set[Path]]",
) -> None:
    """Check and warn if .in files includes .lock constraints or requirements"""
    # pytest -vv --showlocals --log-level INFO -k "test_check_in_includes_lock" tests
    abspath_tests_dir = request.path.parent
    path_pyproject_toml = abspath_tests_dir.joinpath(relpath_pyproject_toml)
    # prepare
    #    pyproject.toml
    path_dest_pyproject_toml = prep_pyproject_toml(path_pyproject_toml, tmp_path, None)
    loader = VenvMapLoader(path_dest_pyproject_toml.as_posix())

    #    has-a feature normally provided by factory Fixing.fix_requirements_lock
    lock_msgs = OutMessages(last_suffix=OutLastSuffix.LOCK)
    unlock_msgs = OutMessages(last_suffix=OutLastSuffix.UNLOCK)

    # prepare -- venv
    # prepare -- requirements folder
    #    venv_path folder. To avoid NotADirectoryError
    prep_these = (
        ".venv/.python-version",
        "requirements/junk.deleteme",
    )
    prepare_folders_files(prep_these, tmp_path)

    #    Copy real .in and .lock files
    for relpath_src in to_requirements_dir:
        abspath_src = abspath_tests_dir.joinpath(relpath_src)
        abspath_dest = tmp_path / "requirements" / abspath_src.name
        shutil.copy(abspath_src.as_posix(), abspath_dest.as_posix())

    # Act
    fixing = Fixing(loader, venv_path, lock_msgs, unlock_msgs)

    msgs_count_actual = len(fixing._out_unlock_messages.fixed_issues)
    assert msgs_count_actual == msgs_count_expected
