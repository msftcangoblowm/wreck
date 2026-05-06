"""
Used only during TYPE_CHECKING

"""

import sys
from contextlib import nullcontext as does_not_raise
from typing import Union

from typing_extensions import TypeAlias

PY310 = sys.version_info[:2] >= (3, 10)
PY311 = sys.version_info[:2] >= (3, 11)

if PY310:
    from types import NoneType  # type: ignore[attr-defined]
else:
    NoneType = type(None)  # type: ignore[misc]

if PY311:
    from typing import Never  # type: ignore[attr-defined]
else:
    from typing_extensions import Never

try:
    from _pytest.python_api import RaisesContext  # noqa: F401
except (ModuleNotFoundError, ImportError):
    # docs say from 8.4+, but actually 8.3.5+
    from _pytest.raises import (  # type: ignore[no-redef, import-not-found]  # noqa: F401
        RaisesExc as RaisesContext,
    )

DOES_NOT_OR_DOES: TypeAlias = Union[does_not_raise[None], RaisesContext[BaseException]]

__all__ = (
    "DOES_NOT_OR_DOES",
    "Never",
    "NoneType",
    "TypeAlias",
)
