"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

There are two ``from_loader`` implementations. Refactor **priority**
is on support for **multiple implementations**, rather than for
performance.

LoaderPinDatum is the latest implementation. Differs from LoaderPin
by reading each requirements file once.

.. csv-table:: Coverage performance comparison
   :header: loader, context, duration(sec)
   :widths: auto

   "LoaderPin", "343 passed, 6 skipped", "82.86"
   "LoaderPinDatum", 343 passed, 6 skipped", "53.19"

.. code-block:: text

   (82.86 - 53.19) / 82.86 = 0.35807 --> ~35.80% speed up

Reducing I/O (file reads), has a significant and high performance impact.

Both implementations hold the result in memory.

:code:`functools.singledispatch` was not used. This pattern is for
multiple implementations based on the first arg, not the return type

.. py:data:: __all__
   :type: tuple[str, str, str, str]
   :value: ("LoaderImplementation", "LoaderPin", "LoaderPinDatum", \
   "from_loader_filepins")

   Module exports

"""

import abc

from pip_requirements_parser import (
    InstallationError,
    RequirementsFile,
)

from .constants import (
    SUFFIX_IN,
    SUFFIX_UNLOCKED,
)
from .exceptions import MissingRequirementsFoldersFiles
from .lock_datum import (
    DATUM,
    Pin,
    PinDatum,
    is_pin,
)
from .lock_filepins import FilePins
from .pep518_venvs import (
    check_loader,
    check_venv_relpath,
    get_reqs,
)

__all__ = (
    "LoaderImplementation",
    "LoaderPin",
    "LoaderPinDatum",
    "from_loader_filepins",
)


def _check_filter_by_pin(val, default=True):
    """Check and correct filter_by_pin arg

    :param val:

       Should be a bool. True to deal with only pins that have specifiers
       and qualifiers

    :type val: typing.Any
    :param default: True unless overridden
    :type default: bool
    :returns: True filter by pins. False all packages
    :rtype: bool
    """
    is_ng = val is None or not isinstance(val, bool)
    if is_ng:
        ret = default
    else:
        ret = val

    return ret


def _from_loader_pins(
    loader,
    venv_path,
    suffix=SUFFIX_UNLOCKED,
    filter_by_pin=True,
):
    """Factory. From a venv, get all Pins.

    :param loader: Contains some paths and loaded not parsed venv reqs
    :type loader: wreck.pep518_venvs.VenvMapLoader
    :param venv_path:

       Relative path to venv base folder. Acts as a key

    :type venv_path: typing.Any
    :param suffix:

       Default ``.unlock``. End suffix of compiled requirements file.
       Either ``.unlock`` or ``.lock``

    :type suffix: str
    :param filter_by_pin: Default True. Filter out entries without specifiers
    :type filter_by_pin: bool | None
    :returns: Feed list[Pin] into class constructor to get an Iterator[Pin]
    :rtype: set[wreck.lock_inspect._T]
    :raises:

        - :py:exc:`wreck.exceptions.MissingRequirementsFoldersFiles` --
          missing requirements file(s). Create it

        - :py:exc:`wreck.exceptions.MissingPackageBaseFolder` --
          loader not provided. Loader provides package base folder


    .. deprecated:: 0.0.1

       drain_swamp.lock_inspect is still around as a reference (bad) implementation
       There is no wreck.lock_inspect

    """
    check_loader(loader)
    filter_by_pin = _check_filter_by_pin(filter_by_pin)

    """Relative path acts as a dict key. An absolute path is not a key.
    Selecting by always nonexistent key returns empty Sequence, abspath_reqs"""
    relpath_venv = check_venv_relpath(loader, venv_path)

    # NotADirectoryError, ValueError, KeyError, MissingRequirementsFoldersFiles
    abspath_reqs = get_reqs(loader, relpath_venv, suffix_last=suffix)

    pins = set()
    for abspath_req in abspath_reqs:

        """Take only enough details to identify package as a pin.

        In .unlock files, ``-c`` and ``-r`` are resolved. Therefore
        ``options`` section will be empty
        """
        try:
            rf = RequirementsFile.from_file(abspath_req)
        except InstallationError as exc:
            msg_exc = (
                f"For venv {venv_path!s}, requirements file not "
                f"found {abspath_req!r}. Create it"
            )
            raise MissingRequirementsFoldersFiles(msg_exc) from exc

        d_rf_all = rf.to_dict()
        rf_reqs = d_rf_all["requirements"]
        has_reqs = (
            rf_reqs is not None and isinstance(rf_reqs, list) and len(rf_reqs) != 0
        )
        if has_reqs:
            for d_req in rf_reqs:
                pkg_name = d_req.get("name", "")
                # list[specifier]
                specifiers = d_req.get("specifier", [])

                # Only keep package which have specifiers e.g. ``pip>=24.2``
                if filter_by_pin is True:
                    if is_pin(specifiers):
                        pin = Pin(abspath_req, pkg_name)
                        pins.add(pin)
                    else:  # pragma: no cover
                        # non-Pin --> filtered out
                        pass
                else:
                    # Do not apply filter. All entries
                    pin = Pin(abspath_req, pkg_name)
                    pins.add(pin)
        else:  # pragma: no cover
            pass
    else:  # pragma: no cover
        pass

    return pins


def from_loader_filepins(
    loader,
    venv_path,
    suffix_last=SUFFIX_IN,
):
    """Load the FilePins

    :param loader: Contains some paths and loaded not parsed venv reqs
    :type loader: wreck.pep518_venvs.VenvMapLoader
    :param venv_path:

       Relative path to venv base folder. Acts as a key

    :type venv_path: typing.Any
    :param suffix:

       Default ``.unlock``. End suffix of compiled requirements file.
       Either ``.unlock`` or ``.lock``

    :type suffix: str
    :returns: All FilePins
    :rtype: list[wreck.lock_filepins.FilePins]
    :raises:

       - :py:exc:`NotADirectoryError` -- venv relative paths do not correspond to
         actual venv folders

       - :py:exc:`ValueError` -- expecting [[tool.venvs]] field reqs to be a
         sequence

       - :py:exc:`KeyError` -- No such venv found

       - :py:exc:`wreck.exceptions.MissingRequirementsFoldersFiles` --
         missing requirements file(s). Create it

       - :py:exc:`wreck.exceptions.MissingPackageBaseFolder` --
         loader invalid. Does not provide package base folder

    """
    check_loader(loader)
    """Relative path acts as a dict key. An absolute path is not a key.
    Selecting by always nonexistent key returns empty Sequence, abspath_reqs"""
    relpath_venv = check_venv_relpath(loader, venv_path)

    # NotADirectoryError, ValueError, KeyError, MissingRequirementsFoldersFiles
    abspath_reqs = get_reqs(loader, relpath_venv, suffix_last=suffix_last)

    fpins = list()
    for abspath_req in abspath_reqs:
        try:
            fp = FilePins(abspath_req)
        except MissingRequirementsFoldersFiles:
            raise
        fpins.append(fp)

    return fpins


def _from_loader_pindatum(
    loader, venv_path, suffix=SUFFIX_UNLOCKED, filter_by_pin=True
):
    """Factory. From a venv, get all Pins.

    This is compatable with
    :py:meth:`Pins.from_loader <wreck.lock_inspect.Pins.from_loader>`

    Disadvantage(only affects .in files): Loss of FilePins benefits
    Advantage: can be used as-is for processing .unlock and .lock files

    :param loader: Contains some paths and loaded not parsed venv reqs
    :type loader: wreck.pep518_venvs.VenvMapLoader
    :param venv_path:

       Relative path to venv base folder. Acts as a key

    :type venv_path: typing.Any
    :param suffix:

       Default ``.unlock``. End suffix of compiled requirements file.
       Either ``.unlock`` or ``.lock``

    :type suffix: str
    :param filter_by_pin: Default True. Filter out entries without specifiers
    :type filter_by_pin: bool | None
    :returns: Feed list[Pin] into class constructor to get an Iterator[Pin]
    :rtype: set[wreck.lock_datum.PinDatum]
    :raises:

       - :py:exc:`NotADirectoryError` -- venv relative paths do not correspond to
         actual venv folders

       - :py:exc:`ValueError` -- expecting [[tool.venvs]] field reqs to be a
         sequence

       - :py:exc:`KeyError` -- No such venv found

       - :py:exc:`wreck.exceptions.MissingRequirementsFoldersFiles` --
         missing requirements file(s). Create it

    """
    check_loader(loader)
    filter_by_pin = _check_filter_by_pin(filter_by_pin)

    fpins = from_loader_filepins(
        loader,
        venv_path,
        suffix_last=suffix,
    )

    pins = set()
    for fpin in fpins:
        for pin in fpin:
            if filter_by_pin is True:
                if is_pin(pin.specifiers):
                    is_add = True
                else:  # pragma: no cover
                    # non-Pin --> filtered out
                    is_add = False
            else:
                is_add = True

            if is_add is True:
                assert isinstance(pin, PinDatum)
                pins.add(pin)
            else:  # pragma: no cover
                pass

    return pins


class LoaderImplementation(abc.ABC):
    """``from_loader`` implementation base type"""

    @abc.abstractmethod
    def __call__(
        self,
        loader,
        venv_path,
        suffix=SUFFIX_UNLOCKED,
        filter_by_pin=True,
    ) -> set[DATUM]:
        """Implementation is a Callable. For the given task, choose
        the cooresponding implementation

        ``.lock`` and ``.unlock`` would expect a Pin

        :param loader: Contains some paths and loaded not parsed venv reqs
        :type loader: wreck.pep518_venvs.VenvMapLoader
        :param venv_path:

           Relative path to venv base folder. Acts as a key

        :type venv_path: typing.Any
        :param suffix:

           Default ``.unlock``. End suffix of compiled requirements file.
           Either ``.unlock`` or ``.lock``

        :type suffix: str
        :param filter_by_pin: Default True. Filter out entries without specifiers
        :type filter_by_pin: bool | None
        :returns: Can either be Pin or PinDatum
        :rtype: set[wreck.lock_datum.DATUM]
        """
        ...


class LoaderPin(LoaderImplementation):
    """Original implementation

    Inefficient cuz reads the file, then reads the file for every pin

    Usage

    .. code-block:: text

       ret: set[wreck.lock_datum.DATUM] = LoaderPin()(loader, venv_path)

    .. deprecated:: 0.0.1

       drain_swamp.lock_inspect is still around as a reference (bad) implementation
       There is no wreck.lock_inspect

    """

    def __call__(
        self,
        loader,
        venv_path,
        suffix=SUFFIX_UNLOCKED,
        filter_by_pin=True,
    ) -> set[DATUM]:
        """Returns a Pin. For signature See the abc"""
        set_ret = _from_loader_pins(
            loader,
            venv_path,
            suffix=suffix,
            filter_by_pin=filter_by_pin,
        )
        return set_ret


class LoaderPinDatum(LoaderImplementation):
    """Another implementation.

    Reads each file once, process all pins once

    Keep in mind, :py:class:`~wreck.lock_loader.LoaderImplementation`
    exists only for compatibility with existing codebase

    Usage

    .. code-block:: text

       ret: set[wreck.lock_datum.DATUM] = LoaderPinDatum()(loader, venv_path)

    """

    def __call__(
        self,
        loader,
        venv_path,
        suffix=SUFFIX_UNLOCKED,
        filter_by_pin=True,
    ) -> set[DATUM]:
        """Returns a PinDatum. For signature See the abc"""
        set_ret = _from_loader_pindatum(
            loader,
            venv_path,
            suffix=suffix,
            filter_by_pin=filter_by_pin,
        )
        return set_ret