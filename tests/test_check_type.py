"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Unittest for module, check_type

.. code-block:: shell

   python -m pytest -vv --showlocals tests/test_check_type.py

Unit test -- Module

.. code-block:: shell

   python -m coverage run --source='wreck.check_type' -m pytest \
   --showlocals tests/test_check_type.py && coverage report \
   --data-file=.coverage --include="**/check_type.py"

"""

from contextlib import nullcontext as does_not_raise
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from wreck.check_type import (
    click_bool,
    is_relative_required,
)
from wreck.constants import SUFFIX_IN

if TYPE_CHECKING:
    from typing import Any

    from tests.typing_only import DOES_NOT_OR_DOES


@pytest.mark.parametrize(
    "relative_path, exts, expectation, expected",
    (
        pytest.param(
            None,
            None,
            pytest.raises(TypeError),
            False,
            id="ext-unsupported-type-None",
        ),
        pytest.param(
            None,
            1.12345,
            pytest.raises(TypeError),
            False,
            id="ext-unsupported-type-float",
        ),
        pytest.param(
            None,
            1,
            pytest.raises(TypeError),
            False,
            id="ext-unsupported-type-int",
        ),
        pytest.param(
            None,
            "Hello world!",
            pytest.raises(TypeError),
            False,
            id="ext-unsupported-type-str-disallowed-sequence",
        ),
        pytest.param(
            None,
            (),
            pytest.raises(ValueError),
            False,
            id="ext-empty-sequence-tuple",
        ),
        pytest.param(
            None,
            [],
            pytest.raises(ValueError),
            False,
            id="ext-empty-sequence-list",
        ),
        pytest.param(
            None,
            (None, 1.12345, 1),
            pytest.raises(ValueError),
            False,
            id="ext-sequence-containing-only-unsupported-types",
        ),
        pytest.param(
            None,
            (SUFFIX_IN,),
            does_not_raise(),
            False,
            id="Path-or-None",
        ),
        pytest.param(
            "requirements/horse.in",
            (SUFFIX_IN,),
            does_not_raise(),
            False,
            id="must-be-a-Path-got-str.-matching-extensions",
        ),
        pytest.param(
            Path("requirements/horse.in"),
            (SUFFIX_IN,),
            does_not_raise(),
            True,
            id="Path-provided-matching-extensions",
        ),
        pytest.param(
            Path("requirements/horse.in"),
            ("in",),
            does_not_raise(),
            True,
            id="autofix-missing-period",
        ),
        pytest.param(
            Path("requirements/horse.in"),
            (".pip",),
            does_not_raise(),
            False,
            id="exts-different-has-.in-expect-.pip",
        ),
        pytest.param(
            Path("requirements/horse.pip"),
            (SUFFIX_IN,),
            does_not_raise(),
            False,
            id="exts-different-has-.pip-expect-.in",
        ),
        pytest.param(
            Path("requirements/horse.in"),
            (".tar", ".gz"),
            does_not_raise(),
            False,
            id="exts-different-has-.in-expect-.tar-or-.gz",
        ),
    ),
)
def test_is_relative_required(
    relative_path: "Path | str | None",
    exts: "Any",
    expectation: "DOES_NOT_OR_DOES",
    expected: bool,
) -> None:
    """Test is_relative_required."""
    # pytest --showlocals --log-level INFO -k "test_is_relative_required" tests
    with expectation:
        actual = is_relative_required(
            path_relative=relative_path,  # type: ignore[arg-type]
            extensions=exts,
        )
    if isinstance(expectation, does_not_raise):
        assert actual == expected


@pytest.mark.parametrize(
    "val, expected",
    (
        pytest.param(
            None,
            None,
            id="None",
        ),
        pytest.param(
            "George",
            None,
            id="Unknown-str",
        ),
        pytest.param(
            "0",
            False,
            id="str-number-indicating-a-bool-value-False",
        ),
        pytest.param(
            "off",
            False,
            id="off-means-False",
        ),
        pytest.param(
            "1",
            True,
            id="str-number-indicating-a-bool-value-True",
        ),
        pytest.param(
            "on",
            True,
            id="off-means-True",
        ),
    ),
)
def test_click_bool(
    val: "str | None",
    expected: "bool | None",
) -> None:
    """Test click.Bool check."""
    # pytest --showlocals --log-level INFO -k "test_click_bool" tests
    actual = click_bool(val=val)
    assert actual is expected
