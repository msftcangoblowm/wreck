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
    is_ok,
    is_relative_required,
)
from wreck.constants import SUFFIX_IN

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import (
        Any,
        Union,
    )

    from tests.typing_only import DOES_NOT_OR_DOES

testdata_is_ok = (
    (None, False),
    ("", False),
    (0.123, False),
    ("    ", False),
    ("Hello World!", True),
)
ids_is_ok = (
    "not str",
    "empty string",
    "not str",
    "contains only whitespace",
    "non-empty string",
)


@pytest.mark.parametrize(
    "mystr, expected",
    testdata_is_ok,
    ids=ids_is_ok,
)
def test_is_ok(
    mystr: "Union[str, float, None]",
    expected: bool,
) -> None:
    """Test is_ok check."""
    # pytest --showlocals --log-level INFO -k "test_is_ok" tests
    actual = is_ok(mystr)
    assert actual == expected


if TYPE_CHECKING:
    testdata_is_relative_required: Sequence[
        tuple[Union[Path, str, None], Any, DOES_NOT_OR_DOES, bool]
    ]

testdata_is_relative_required = (
    (None, None, pytest.raises(TypeError), False),
    (None, 1.12345, pytest.raises(TypeError), False),
    (None, 1, pytest.raises(TypeError), False),
    (None, "Hello world!", pytest.raises(TypeError), False),
    (None, (), pytest.raises(ValueError), False),
    (None, [], pytest.raises(ValueError), False),
    (None, (None, 1.12345, 1), pytest.raises(ValueError), False),
    (None, (SUFFIX_IN,), does_not_raise(), False),
    ("requirements/horse.in", (SUFFIX_IN,), does_not_raise(), False),
    (Path("requirements/horse.in"), (SUFFIX_IN,), does_not_raise(), True),
    (Path("requirements/horse.in"), ("in",), does_not_raise(), True),
    (Path("requirements/horse.in"), (".pip",), does_not_raise(), False),
    (
        Path("requirements/horse.pip"),
        (SUFFIX_IN,),
        does_not_raise(),
        False,
    ),
    (Path("requirements/horse.in"), (".tar", ".gz"), does_not_raise(), False),
)
ids_is_relative_required = (
    "ext unsupported type None",
    "ext unsupported type float",
    "ext unsupported type int",
    "ext unsupported type str disallowed sequence",
    "ext empty sequence tuple",
    "ext empty sequence list",
    "ext sequence containing only unsupported types",
    "Path | None",
    "must be a Path, got str. matching extensions",
    "Path provided matching extensions",
    "autofix missing period",
    "exts different has .in expect .pip",
    "exts different has .pip expect .in",
    "exts different has .in expect .tar or .gz",
)


@pytest.mark.parametrize(
    "relative_path, exts, expectation, expected",
    testdata_is_relative_required,
    ids=ids_is_relative_required,
)
def test_is_relative_required(
    relative_path: "Union[Path, str, None]",
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


testdata_click_bool = (
    (None, None),
    ("George", None),
    ("0", False),
    ("off", False),
    ("1", True),
    ("on", True),
)
ids_click_bool = (
    "None",
    "Unknown str",
    "str number indicating a bool value False",
    "off means False",
    "str number indicating a bool value True",
    "off means True",
)


@pytest.mark.parametrize(
    "val, expected",
    testdata_click_bool,
    ids=ids_click_bool,
)
def test_click_bool(
    val: "Union[str, None]",
    expected: "Union[bool, None]",
) -> None:
    """Test click.Bool check."""
    # pytest --showlocals --log-level INFO -k "test_click_bool" tests
    actual = click_bool(val=val)
    assert actual is expected
