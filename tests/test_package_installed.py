"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Checks if a Python package is installed

Without coverage

.. code-block:: shell

   python -m pytest -vv --showlocals tests/test_package_installed.py

With coverage

.. code-block:: shell

   python -m coverage run --source='wreck._package_installed' -m pytest \
   --showlocals tests/test_package_installed.py && coverage report \
   --data-file=.coverage --include="**/_package_installed.py"

"""

import pytest

from wreck._package_installed import is_package_installed
from wreck.constants import g_app_name


@pytest.mark.parametrize(
    "app_name, is_installed",
    (
        pytest.param(
            "blarneys_blowup_doll",
            False,
            id="no-such-package",
        ),
        pytest.param(
            g_app_name,
            True,
            id="package-exists",
        ),
    ),
)
def test_is_package_installed(app_name: str, is_installed: bool) -> None:
    """Check if package is installed or not"""
    # pytest --showlocals --log-level INFO -k "test_is_package_installed" tests
    assert is_package_installed(app_name) is is_installed
