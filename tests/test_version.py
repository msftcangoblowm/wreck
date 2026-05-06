"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Unit test -- Module

.. code-block:: shell

   python -m coverage run --source='wreck._version' -m pytest \
   --showlocals tests/test_version.py && coverage report \
   --data-file=.coverage --include="**/_version.py"

"""

from contextlib import nullcontext as does_not_raise
from typing import TYPE_CHECKING

import pytest
from packaging.version import Version

try:
    from wreck._version import (
        __version__,
        version_tuple,
    )
except (ModuleNotFoundError, ImportError):
    reason = "No module _version. Create it"
    pytest.xfail(reason)

if TYPE_CHECKING:
    from typing import Union

    from tests.typing_only import DOES_NOT_OR_DOES

testdata_version_file = (
    (
        __version__,
        version_tuple,
        does_not_raise(),
        __version__,
    ),
)
ids_version_file = ("check valid semantic version str",)


@pytest.mark.parametrize(
    "version_package_str, version_package_tuple, expectation, expected_version",
    testdata_version_file,
    ids=ids_version_file,
)
def test_version_file(
    version_package_str: str,
    version_package_tuple: "tuple[int, int, int, Union[str, None]]",
    expectation: "DOES_NOT_OR_DOES",
    expected_version: str,
) -> None:
    """Why is this file not skipped"""
    # pytest -s -vv --showlocals -k "test_version_file" tests
    assert isinstance(version_package_str, str)
    assert isinstance(version_package_tuple, tuple)

    # act
    """confirm the version str in wreck._version is valid and Doesn't
    raise an exception"""
    with expectation:
        ver_actual = Version(version_package_str)
    if isinstance(expectation, does_not_raise):
        ver_actual_str = str(ver_actual)
        assert ver_actual_str == expected_version
