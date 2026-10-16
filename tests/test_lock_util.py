"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Without coverage

.. code-block:: shell

   python -m pytest -vv --showlocals tests/test_lock_util.py

With coverage

.. code-block:: shell

   python -m coverage run --source='wreck.lock_util' -m pytest \
   --showlocals tests/test_lock_util.py && coverage report \
   --data-file=.coverage --include="**/lock_util.py"

"""

import site
from contextlib import nullcontext as does_not_raise
from pathlib import (
    Path,
    PurePath,
)
from typing import (
    TYPE_CHECKING,
    cast,
)

import pytest
from logging_strict.tech_niques import get_locals_dynamic  # noqa: F401

from wreck._safe_path import resolve_joinpath
from wreck.constants import (  # g_app_name,  # noqa: F401
    SUFFIX_IN,
    SUFFIX_LOCKED,
    SUFFIX_SHARED_IN,
    SUFFIX_UNLOCKED,
)
from wreck.lock_util import (
    abspath_relative_to_package_base_folder,
    check_relpath,
    is_shared,
    is_suffixes_ok,
    replace_suffixes_last,
)

if TYPE_CHECKING:
    from collections.abc import (
        Callable,
        MutableSet,
        Sequence,
    )
    from typing import Union

    from tests.typing_only import DOES_NOT_OR_DOES


@pytest.mark.parametrize(
    "file_name, expectation, expected_is_shared",
    (
        pytest.param(
            f"dog{SUFFIX_IN}",
            does_not_raise(),
            False,
            id=SUFFIX_IN,
        ),
        pytest.param(
            f"dog{SUFFIX_SHARED_IN}",
            does_not_raise(),
            True,
            id=SUFFIX_SHARED_IN,
        ),
        pytest.param(
            f"dog{SUFFIX_LOCKED}",
            does_not_raise(),
            False,
            id=SUFFIX_LOCKED,
        ),
        pytest.param(
            f"dog.shared{SUFFIX_LOCKED}",
            does_not_raise(),
            True,
            id=f".shared{SUFFIX_LOCKED}",
        ),
        pytest.param(
            f"dog{SUFFIX_UNLOCKED}",
            does_not_raise(),
            False,
            id=SUFFIX_UNLOCKED,
        ),
        pytest.param(
            f"dog.shared{SUFFIX_UNLOCKED}",
            does_not_raise(),
            True,
            id=f".shared{SUFFIX_UNLOCKED}",
        ),
        pytest.param(
            "dog",
            does_not_raise(),
            False,
            id="no-suffixes",
        ),
        pytest.param(
            "dog.shared",
            does_not_raise(),
            True,
            id="no-ending-.shared",
        ),
        pytest.param(
            None,
            pytest.raises(ValueError),
            False,
            id="None",
        ),
        pytest.param(
            "",
            pytest.raises(ValueError),
            False,
            id="empty-str",
        ),
        pytest.param(
            "   ",
            pytest.raises(ValueError),
            False,
            id="just-whitespace",
        ),
        pytest.param(
            1.2345,
            pytest.raises(ValueError),
            False,
            id="unsupported-type",
        ),
    ),
)
def test_lock_util_is_shared(
    file_name: "Union[float, str, None]",
    expectation: "DOES_NOT_OR_DOES",
    expected_is_shared: bool,
) -> None:
    """Test is_shared."""
    # pytest --showlocals --log-level INFO -k "test_lock_util_is_shared" tests
    with expectation:
        actual = is_shared(
            file_name,  # type: ignore[arg-type]
        )
    if isinstance(expectation, does_not_raise):
        """
        args = (file_name,)
        kwargs = {}
        t_ret = get_locals_dynamic(is_shared, *args, **kwargs)
        """
        pass

        assert actual is expected_is_shared


@pytest.mark.parametrize(
    "file_name, suffix, expectation, expected_file_name",
    (
        pytest.param(
            "dog",
            SUFFIX_IN,
            does_not_raise(),
            f"dog{SUFFIX_IN}",
            id="No-suffix",
        ),
        pytest.param(
            "dog.shared",
            SUFFIX_IN,
            does_not_raise(),
            f"dog{SUFFIX_SHARED_IN}",
            id=f"add-suffix-{SUFFIX_IN}",
        ),
        pytest.param(
            f"dog.shared{SUFFIX_UNLOCKED}",
            SUFFIX_IN,
            does_not_raise(),
            f"dog{SUFFIX_SHARED_IN}",
            id=f".shared{SUFFIX_UNLOCKED}--{SUFFIX_SHARED_IN}",
        ),
    ),
)
def test_replace_suffixes_last(
    file_name: str,
    suffix: str,
    expectation: "DOES_NOT_OR_DOES",
    expected_file_name: str,
    tmp_path: "Path",
    prepare_folders_files: "Callable[[Union[Sequence[Union[str, Path]], MutableSet[Union[str, Path]]], Path], set[Path]]",
) -> None:
    """Test replace_suffixes_last."""
    # pytest --showlocals --log-level INFO -k "test_replace_suffixes_last" tests
    # prepare
    prepare_these = (file_name,)
    set_files_dest = prepare_folders_files(prepare_these, tmp_path)

    # Act
    for abspath_f in set_files_dest:
        with expectation:
            actual_f = replace_suffixes_last(abspath_f, suffix)
        if isinstance(expectation, does_not_raise):
            # Verify
            actual_file_name = actual_f.name
            assert actual_file_name == expected_file_name

        # PurePath
        with pytest.raises(TypeError):
            replace_suffixes_last(PurePath(abspath_f), suffix)

        # Not a Path
        with pytest.raises(TypeError):
            replace_suffixes_last(1.2345, suffix)

        # relative path --> ValueError
        with pytest.raises(ValueError):
            relpath_f = abspath_f.relative_to(tmp_path)
            replace_suffixes_last(relpath_f, suffix)


@pytest.mark.parametrize(
    "relpath, stem, expectation",
    (
        pytest.param(
            "requirements/prod.shared",
            "prod.shared",
            pytest.raises(ValueError),
            id="no-ENDING",
        ),
        pytest.param(
            "requirements/prod",
            "prod",
            pytest.raises(ValueError),
            id="No-suffixes",
        ),
        pytest.param(
            "requirements/prod.shared.frog",
            "prod.shared",
            pytest.raises(ValueError),
            id=".shared-then-unknown-ENDING",
        ),
        pytest.param(
            "requirements/prod.frog",
            "prod",
            pytest.raises(ValueError),
            id="unknown-ENDING",
        ),
        pytest.param(
            7.4,
            "prod",
            pytest.raises(TypeError),
            id="unsupported-type",
        ),
        pytest.param(
            "requirements/prod.shared.in",
            "prod.shared.in",
            does_not_raise(),
            id="acceptable-relative-path",
        ),
        pytest.param(
            Path("requirements/prod.shared.in"),
            "prod.shared.in",
            does_not_raise(),
            id="acceptable-relative-Path",
        ),
    ),
)
def test_is_suffixes_ok(
    relpath: "Union[str, Path, float]",
    stem: str,
    expectation: "DOES_NOT_OR_DOES",
) -> None:
    """Test is_suffixes_ok. Demonstrate invalid relpath."""
    # pytest --showlocals --log-level INFO -k "test_is_suffixes_ok" tests
    with expectation:
        is_suffixes_ok(
            relpath,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "relpath, expectation",
    (
        pytest.param(
            Path("requirements/pip.in"),
            does_not_raise(),
            id="pip.in-1-constraint-3-requirements",
        ),
    ),
)
def test_check_relpath(
    relpath: "Path",
    expectation: "DOES_NOT_OR_DOES",
    path_project_base: "Callable[[], Path]",
    tmp_path: "Path",
) -> None:
    """check_relpath is relpath relative to cwd"""
    # pytest --showlocals --log-level INFO -k "test_check_relpath" tests
    # prepare
    path_cwd = path_project_base()

    # prepare
    path_f_in_tmp = cast("Path", resolve_joinpath(tmp_path, "deleteme.txt"))
    path_f_in_tmp.touch()
    # no touch
    path_f_in_cwd = cast("Path", resolve_joinpath(path_cwd, "deleteme.txt"))

    # unsupported type --> TypeError
    invalids = (
        None,
        1.234,
    )
    for invalid in invalids:
        with pytest.raises(TypeError):
            check_relpath(path_cwd, invalid)

    # no such file --> FileNotFoundError
    with pytest.raises(FileNotFoundError):
        check_relpath(path_cwd, path_f_in_cwd)

    # not relative to base folder --> ValueError
    with pytest.raises(ValueError):
        check_relpath(path_cwd, path_f_in_tmp)

    # file exists relative to cwd. No exception raised
    with expectation:
        check_relpath(path_cwd, relpath)


@pytest.mark.parametrize(
    "abspath_f, constraint_relpath, expectation, expected_relpath",
    (
        pytest.param(
            Path(__file__).parent.parent.joinpath(
                "docs",
                "pip-tools.in",
            ),
            "../requirements/pins.shared.in",
            does_not_raise(),
            "requirements/pins.shared.in",
            id="different-folders",
        ),
        pytest.param(
            Path(__file__).parent.parent.joinpath(
                "docs",
                "pip-tools.in",
            ),
            "../requirements/dogfood.shared.in",
            pytest.raises(FileNotFoundError),
            "requirements/dogfood.shared.in",
            id="impossible-to-resolve-requirements-file-not-found",
        ),
        pytest.param(
            Path(site.getuserbase()),
            "../requirements/dogfood.shared.in",
            pytest.raises(ValueError),
            "requirements/dogfood.shared.in",
            id="not-subpath-not-relative-to",
        ),
    ),
)
def test_abspath_relative_to_package_base_folder(
    abspath_f: "Path",
    constraint_relpath: str,
    expectation: "DOES_NOT_OR_DOES",
    expected_relpath: str,
    path_project_base: "Callable[[], Path]",
) -> None:
    """Normalize requirement file constraint or requirement relpath to cwd"""
    # pytest --showlocals --log-level INFO -k "test_abspath_relative_to_package_base_folder" tests
    # prepare
    path_cwd = path_project_base()

    with expectation:
        abspath_actual = abspath_relative_to_package_base_folder(
            path_cwd,
            abspath_f,
            constraint_relpath,
        )
    if isinstance(expectation, does_not_raise):
        relpath_actual = abspath_actual.relative_to(path_cwd)
        assert relpath_actual.as_posix() == expected_relpath
