"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Unit test -- Module

.. code-block:: shell

   python -m coverage run --source='wreck._version' -m pytest \
   --showlocals tests/test_version.py && coverage report \
   --data-file=.coverage --include="**/_version.py"

"""

from contextlib import nullcontext as does_not_raise

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


def test_version_file():
    """Why is this file not skipped"""
    # pytest --showlocals --log-level INFO -k "test_version_file" tests
    assert isinstance(__version__, str)
    assert isinstance(version_tuple, tuple)

    # act
    """confirm the version str in wreck._version is valid and Doesn't
    raise an exception"""
    expectation = does_not_raise()
    with expectation:
        ver = Version(__version__)
    if isinstance(expectation, does_not_raise):
        assert str(ver) == __version__
