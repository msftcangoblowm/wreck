"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

.. py:data:: DC_SLOTS
   :type: dict[str, bool]

   Allows dataclasses.dataclass __slots__ support from py310

.. py:data:: TOML_SECTION_VENVS
   :type: str
   :value: "wreck.venvs"

   pyproject.toml section excluding ``tool.`` prefix

.. py:data:: DICT_SEARCH_KEY
   :type: str
   :value: "venv_base_path"

   In pyproject.toml section, key name. The value contains the venv relative path

"""

import os
import sys
from collections.abc import (
    Iterator,
    Sequence,
)
from dataclasses import (
    InitVar,
    dataclass,
    field,
)
from pathlib import (
    Path,
    PurePath,
    PurePosixPath,
)
from typing import (
    TYPE_CHECKING,
    Union,
    cast,
)

from ._safe_path import (
    replace_suffixes,
    resolve_joinpath,
)
from .check_type import is_ok
from .constants import (
    SUFFIX_IN,
    g_app_name,
)
from .exceptions import (
    MissingPackageBaseFolder,
    MissingRequirementsFoldersFiles,
)
from .lock_util import (
    is_shared,
    replace_suffixes_last,
)
from .monkey.patch_pyproject_reading import (
    PyProjectData,
    ReadPyproject,
)
from .monkey.pyproject_reading import TOML_RESULT
from .pep518_read import find_pyproject_toml

# Use dataclasses slots True for reduced memory usage and performance gain
if sys.version_info >= (3, 10):  # pragma: no cover py-gte-310-else
    DC_SLOTS = {"slots": True}
else:  # pragma: no cover py-gte-310
    DC_SLOTS = {}

TOML_SECTION_VENVS = f"{g_app_name}.venvs"
DICT_SEARCH_KEY = "venv_base_path"


def check_venv_relpath(loader, venv_path_mixed):
    """Expecting relpath. If abspath convert to relpath

    Relative path acts as a dict key. An absolute path is not a key.
    Selecting by always nonexistent key returns empty Sequence, abspath_reqs

    Assume loader has been checked

    :param loader: Contains some paths and loaded not parsed venv reqs
    :type loader: wreck.pep518_venvs.VenvMapLoader
    :param venv_path_mixed:

       Relative path to venv base folder. Acts as a key

    :type venv_path_mixed: typing.Any
    :returns: relative Path to venv base folder
    :rtype: pathlib.Path
    """
    is_abs_path = is_ok(venv_path_mixed) and Path(venv_path_mixed).is_absolute()
    is_abspath = (
        venv_path_mixed is not None
        and issubclass(type(venv_path_mixed), PurePath)
        and venv_path_mixed.is_absolute()
    )
    if is_abs_path:
        # abspath str
        abspath_val = Path(venv_path_mixed)
        relpath_venv = Path(abspath_val.relative_to(loader.project_base).as_posix())
    elif is_abspath:
        # abspath Path
        abspath_val = venv_path_mixed
        relpath_venv = Path(abspath_val.relative_to(loader.project_base).as_posix())
    else:  # pragma: no cover
        # relpath str|Path -> Path
        relpath_venv = Path(venv_path_mixed)

    return relpath_venv


@dataclass(**DC_SLOTS)
class VenvReq:
    """Can always apply project_base to get the absolute Path

    .. py:attribute:: project_base
       :type: pathlib.Path

       Absolute path to project base folder

    .. py:attribute:: venv_relpath
       :type: str

       As sourced from TOML file a str (single quoted) relative path to venv base folder

    .. py:attribute:: req_relpath
       :type: str

       As sourced from TOML file a str (single quoted) relative path to requirement file
       w/o (end) suffix: ``.in``, ``.unlock``, ``.lock``. So a shared (between venv)
       requirement file, would be written ``requirements/prod.shared`` w/o the final
       suffix e.g. ``.in``.

    .. py:attribute:: req_folders
       :type: tuple[str]

       req folders relative path. Requirement files should not be outside these folders.
       Intentionally, cannot specify additional folders.

    """

    project_base: Path
    venv_relpath: str
    req_relpath: str
    req_folders: tuple[str]

    def __repr__(self):
        """Create a realistic repr that shows absolute paths

        :returns: repr that shows absolute paths rather than relative paths
        :rtype: str
        """
        cls_name = self.__class__.__name__
        ret = (
            f"<{cls_name} "
            f"project_base='{self.project_base!r}', "
            f"venv_relpath='{self.venv_abspath!s}', "
            f"req_relpath='{self.req_abspath!s}', "
            f"req_folders='{self.req_folders!s}'>"
        )
        return ret

    @property
    def venv_abspath(self):
        """Get abspath for venv.

        Stored in TOML file as a relative path (str).

        :returns: venv absolute Path
        :rtype: pathlib.Path
        """
        ret = cast("Path", resolve_joinpath(self.project_base, self.venv_relpath))

        return ret

    @property
    def req_abspath(self):
        """Get abspath for requirement. If lacks a ``.in`` append it

        Stored in TOML file as a relative path (str).

        :returns: venv absolute Path
        :rtype: pathlib.Path
        """
        ret_maybe_suffix = cast(
            "Path",
            resolve_joinpath(self.project_base, self.req_relpath),
        )
        if self.is_req_shared:
            # .shared --> .shared.in
            ret = cast("Path", replace_suffixes(ret_maybe_suffix, ".shared.in"))
        else:
            # .unlock, .lock, .in --> .in
            ret = cast("Path", replace_suffixes(ret_maybe_suffix, ".in"))

        return ret

    @property
    def is_req_shared(self):
        """Check if requirement file suffix is ``.shared``. Indicating
        requirement file is shared with multiple venv. And thus not an
        ideal place for nudge pins

        :returns: True if requirements file has a .shared suffix
        :rtype: bool
        """
        ret_maybe_suffix = cast(
            "Path",
            resolve_joinpath(self.project_base, self.req_relpath),
        )
        ret = is_shared(ret_maybe_suffix.name)

        return ret

    def _req_folders_abspath(self):
        """Generator of absolute path to requirement folders.
        There should be no requirements files outside of these folders

        :returns: Generator of absolute path to requirement folders
        :rtype: collections.abc.Generator[pathlib.Path, None, None]
        """
        for dir_relpath in self.req_folders:
            req_dir_abspath = cast(
                "Path",
                resolve_joinpath(self.project_base, dir_relpath),
            )
            yield req_dir_abspath
        yield from ()

    def reqs_all(self, suffix=SUFFIX_IN):
        """Yields abspath to requirements files. The suffix
        filters by requirements file type

        :param suffix: Specific requirements file type
        :type suffix: str
        :returns: Generator of absolute path to requirement folders
        :rtype: collections.abc.Generator[pathlib.Path, None, None]
        """
        pattern = f"**/*{suffix}"
        for req_dir_abspath in self._req_folders_abspath():
            yield from req_dir_abspath.glob(pattern)

        yield from ()


@dataclass(**DC_SLOTS)
class VenvMapLoader:
    """Load the pyproject.toml ``[[tool.wreck.venvs]]`` section

    :ivar pyproject_toml_base_path:

       Start path for the reverse search to find ``pyproject.toml`` file

    :vartype: str

    .. py:attribute:: project_base
       :type: pathlib.Path

       Package base folder absolute path

    .. py:attribute:: pyproject_toml
       :type: pathlib.Path

       pyproject.toml absolute path

    .. py:attribute:: l_data
       :type: collections.abc.Sequence[wreck.monkey.pyproject_reading.TOML_RESULT]

       TOML section ``[[tool.wreck.venvs]]`` are array of tables. Reading this
       produces a list of Mapping

    .. py:attribute:: section_parent
       :type: wreck.monkey.pyproject_reading.TOML_RESULT

       venv array of tables parent section. Does not include itself.
       Intended to contain behavioral variables only. key/value pair
       validation is needed.

    """

    pyproject_toml_base_path: InitVar[str]
    project_base: Path = field(init=False)
    pyproject_toml: Path = field(init=False)
    l_data: Sequence[TOML_RESULT] = field(init=False, default_factory=list)
    section_parent: TOML_RESULT = field(init=False, default_factory=dict)

    def __post_init__(self, pyproject_toml_base_path):
        """Load data. Preferable if this occurs only once."""
        cls = type(self)
        # May raise TypeError, FileNotFoundError, or LookupError
        t_data = cls.load_data(pyproject_toml_base_path)
        l_data, d_parent, project_base, pyproject_toml = t_data
        self.project_base = project_base
        self.pyproject_toml = pyproject_toml
        self.l_data = l_data
        self.section_parent = d_parent

    @staticmethod
    def load_data(pyproject_toml_base_path):
        """From a path do a reverse search to find a ``pyproject.toml``
        or a ``.pyproject_toml`` test file.

        The venvs and venv's requirements won't change. Possible some files are
        missing. So the load process needs to only occur once.

        :param pyproject_toml_base_path:

           Start path for the reverse search to find ``pyproject.toml`` file

        :type: str
        :returns: TOML project and one section data along with a few paths
        :rtype:

           tuple[collections.abc.Sequence[wreck.monkey.pyproject_reading.TOML_RESULT], TOML_RESULT, pathlib.Path, pathlib.Path]

        :raises:

           - :py:exc:`FileNotFoundError` -- pyproject.toml file reverse search
             start path expecting Path or file not found

           - :py:exc:`LookupError` -- no [[tools.wreck.venvs]] TOML array of tables

        """
        # Find pyproject.toml path
        srcs = (pyproject_toml_base_path,)
        pyproject_toml_abspath = find_pyproject_toml(srcs, None)

        is_ng = pyproject_toml_abspath is None or not isinstance(
            pyproject_toml_abspath, str
        )
        if is_ng:
            # None indicates file not found. If found will be an abspath str
            msg_exc = (
                "pyproject.toml file reverse search start path expecting "
                f"str path got {type(pyproject_toml_abspath)}"
            )
            raise FileNotFoundError(msg_exc)
        else:  # pragma: no cover
            str_pyproject_toml = cast(
                "Union[str, os.PathLike[str]]",
                pyproject_toml_abspath,
            )

        abspath_pyproject_toml = Path(str_pyproject_toml)

        # Read and parse pyproject.toml section
        # If path=None, defaults to Path("pyproject.toml")
        try:
            proj_data: PyProjectData = ReadPyproject()(
                path=abspath_pyproject_toml,
                tool_name=TOML_SECTION_VENVS,
                key_name=DICT_SEARCH_KEY,
                is_expect_list=True,
            )
            l_data = cast("Sequence[TOML_RESULT]", proj_data.section)
            d_parent = cast("TOML_RESULT", proj_data.section_parent)
        except LookupError:
            raise

        pyproject_toml = abspath_pyproject_toml
        project_base = abspath_pyproject_toml.parent

        return l_data, d_parent, project_base, pyproject_toml

    @property
    def venv_relpaths(self):
        """Get venvs' relative path.

        Supplements parse_data

        :returns: venvs' relative path
        :rtype: tuple[pathlib.Path]
        """
        lst = []
        for d_venv in self.l_data:
            if "venv_base_path" in d_venv.keys():
                venv_relpath = d_venv.get("venv_base_path", None)
                if venv_relpath is not None:
                    lst.append(venv_relpath)
                else:  # pragma: no cover
                    pass
            else:  # pragma: no cover
                pass

        return tuple(lst)

    def parse_data(
        self,
        parse_venv_relpath=None,
        check_suffixes=(".in", ".unlock", ".lock"),
    ):
        """Take raw TOML section array of tables and parse.

        Each datum is stored along with redundant metadata project_base and in_folder.
        :param check_suffixes:

           Default (".in", ".unlock", ".lock"). Suffixes of requirements file to
           check exists and is file

        :type check_suffixes: tuple[str, ...]
        :returns: All VenvReq and missing files
        :rtype: tuple[list[wreck.pep518_venvs.VenvReq], list[str]]

        :raises:

           - :py:exc:`NotADirectoryError` -- venv relative paths do not correspond to
             actual venv folders

           - :py:exc:`ValueError` -- expecting [[tool.wreck.venvs]] field reqs to be a
             sequence

        """
        if TYPE_CHECKING:
            venv_reqs: list[VenvReq]
            lst_missing: list[str]
            lst_missing_loc: list[str]

        # Sequence[str] | None
        check_suffixes_local = fix_check_suffixes(check_suffixes)
        if check_suffixes_local is None:
            check_suffixes_local = (".in", ".unlock", ".lock")
        else:  # pragma: no cover
            pass

        venv_reqs = []
        lst_missing = []
        msg_exc_field_type_ng = "Expecting requirements to be a list[str]"
        for d_venv in self.l_data:
            venv_relpath = d_venv.get("venv_base_path", None)

            # Skip parsing of other venv requirements
            if (
                parse_venv_relpath is not None
                and isinstance(parse_venv_relpath, str)
                and venv_relpath != parse_venv_relpath
            ):
                continue

            # deprecate in_folder
            # in_folder = d_venv.get("in_folder", None)

            # list comprehension creates a list[list[whatever]]
            # Just want a list[whatever]
            reqs = []
            for k, v in d_venv.items():
                if k == "reqs":
                    # Check type(v) is Sequence and not one str
                    is_unsupported_types = not isinstance(v, Sequence) or (
                        isinstance(v, Sequence) and isinstance(v, str)
                    )
                    if is_unsupported_types:
                        raise ValueError(msg_exc_field_type_ng)
                    else:  # pragma: no cover
                        pass

                    reqs.extend(v)
                else:  # pragma: no cover
                    pass

            # Check venv is a folder
            abspath_venv = cast(
                "Path",
                resolve_joinpath(self.project_base, venv_relpath),
            )
            if not abspath_venv.is_dir():
                msg_exc = (
                    "All venv base folder(s) must exist. Missing folder "
                    f"{abspath_venv!r}. Create it"
                )
                raise NotADirectoryError(msg_exc)
            else:  # pragma: no cover
                pass

            # from reqs, find all folders' relative path
            # These folders constitute all folders that contain requirements files
            set_relpath_folders = set()
            for req in reqs:
                req_folder_relpath = str(PurePosixPath(req).parent)
                set_relpath_folders.add(req_folder_relpath)
            t_relpath_folders = tuple(set_relpath_folders)

            # Check req
            lst_missing_loc = []

            # Check file existence. Excludes support files

            for req in reqs:
                vr = VenvReq(self.project_base, venv_relpath, req, t_relpath_folders)

                check_these = []
                for check_suffix in check_suffixes_local:
                    abspath_req = replace_suffixes_last(vr.req_abspath, check_suffix)
                    check_these.append(abspath_req)

                lst_not_found = [
                    path_f for path_f in check_these if not path_f.is_file()
                ]
                is_not_founds = len(lst_not_found) != 0
                if is_not_founds:
                    msg_missing = (
                        f"For venv: {venv_relpath!s}, missing requirements: "
                        f"{lst_not_found!r}. "
                        "One possibility is file name changed. "
                        "Search for requirement relative path in "
                        "pyproject.toml [[tool.venv]] sections or "
                        "in requirements files"
                    )
                    lst_missing_loc.append(msg_missing)
                else:  # pragma: no cover
                    pass
                # Anyway store VenvReq. TOML loads func removes dups
                venv_reqs.append(vr)

            lst_missing.extend(lst_missing_loc)

        t_ret = venv_reqs, lst_missing

        return t_ret

    def ensure_abspath(self, key):
        """Support key being either relative or absolute path

        :param key: venv path. Either relative or absolute path
        :type key: str | pathlib.Path
        :returns: venv absolute Path
        :rtype: pathlib.Path
        :raises:

           - :py:exc:`TypeError` -- unsupported type expecting str or pathlib.Path

        """
        msg_exc_key_ng = f"venv {key!r} not a str got {type(key)}"

        is_acceptable_type = key is not None and (
            (isinstance(key, str) and len(key.strip()) != 0)
            or issubclass(type(key), PurePath)
        )

        if not is_acceptable_type:
            raise TypeError(msg_exc_key_ng)
        else:  # pragma: no cover
            pass

        p = Path(key)
        if not p.is_absolute():
            key_abspath = cast(
                "Path",
                resolve_joinpath(self.project_base, key),
            )
        else:
            key_abspath = p

        return key_abspath


class VenvMap(Iterator[VenvReq]):
    """From ``pyproject.toml``, read [[tool.wreck.venvs]] array of tables.

    Each virtual environment should have a list of requirement files which
    maybe can recreate it.

    The venv relative path and the requirements files relative paths are both posix.
    The **top level** requirements file paths are w/o suffix.

    Complete example venvs and respective list of requirement files

    .. code-block:: text

       [[tool.wreck.venvs]]
       venv_base_path = '.doc/.venv'
       in_folder = 'docs'
       reqs = [
           'docs/pip-tools',
           'docs/requirements',
       ]
       [[tool.wreck.venvs]]
       venv_base_path = '.venv'
       in_folder = 'requirements'
       reqs = [
           'requirements/pip-tools',
           'requirements/pip',
           'requirements/prod.shared',
           'requirements/kit',
           'requirements/tox',
           'requirements/mypy',
           'requirements/manage',
           'requirements/dev',
       ]

    - In TOML format, paths **MUST** be single quoted.

    - Note lack of suffix.

      There are three suffix per requirements: ``.in``, ``.unlock``, and ``.lock``.

    - The venv folder **should** already exist.

      The focus is on the requirements files, **not** what's install
      within the virtual environment.

    - The requirements files **should** already exist.

      As long as the ``.in`` files exist, to recreate
      ``.lock`` and ``.unlock`` -- :code:`reqs fix`
      ``.unlock`` --  :code:`reqs unlock`

    :ivar _loader:

       Contains some paths and loaded unparsed mappings

    :vartype _loader: wreck.pep518_venvs.VenvMapLoader
    :ivar check_suffixes:

       Default (".in", ".unlock", ".lock"). Suffixes of requirements file to
       check exists and is file

    :vartype check_suffixes: tuple[str, ...]

    .. py:attribute:: _iter
       :type: collections.abc.Iterator[wreck.pep518_venvs.VenvReq]

       Package base folder absolute path

    .. py:attribute:: _venvs
       :type: list[wreck.pep518_venvs.VenvReq]

       key is virtual environment absolute path as_posix. Value is a
       list of absolute path to top level ``.in`` requirement files

       To change suffix, use :py:func:`wreck._safe_path.replace_suffixes`

    .. py:attribute:: _missing

       Make missing requirements available. Then at a convenient time
       can provide feedback on missing requirements files

    .. py:attribute:: __slots__
       :value: ("_loader", "_venvs", "_iter", "_missing")

       Reduce memory footprint. Enhance performance

    :raises:

       - :py:exc:`TypeError` -- pyproject.toml file reverse search
         start path expecting Path

       - :py:exc:`FileNotFoundError` -- pyproject.toml not found

       - :py:exc:`LookupError` -- no [[tools.wreck.venvs]] TOML array of tables

       - :py:exc:`NotADirectoryError` -- venv relative paths do not correspond to
         actual venv folders

    """

    _loader: VenvMapLoader
    _iter: Iterator[VenvReq]
    _venvs: list[VenvReq]
    _missing: list[str]

    __slots__ = ("_loader", "_venvs", "_iter", "_missing")

    def __init__(
        self,
        loader,
        parse_venv_relpath=None,
        check_suffixes=(".in", ".unlock", ".lock"),
    ):
        """Class constructor."""
        # Load data should occur once. Not each iteration.
        self._loader = loader

        venvs, missing = self._loader.parse_data(
            parse_venv_relpath=parse_venv_relpath,
            check_suffixes=check_suffixes,
        )

        """Simplifies a Mapping down into a list[dataclass]. Each item
        contains both key and values"""
        self._venvs = venvs

        self._missing = missing

        # initialize iterator
        self._iter = iter(self._venvs)

    @property
    def missing(self):
        """During each iteration, check that requirement files exists
        is performed. The results are stored rather than raising exceptions.

        Checks for existence of ``.in``, ``.unlock`` and ``.lock`` files.

        Does not check for ``.lnk``

        :returns: venv
        :rtype: list[str]
        """
        return self._missing

    @property
    def project_base(self):
        """The loader reveals the project base folder by conducting a
        reverse search. Only for codebases which also requires the project base.

        :returns: Project base path
        :rtype: pathlib.Path

        .. seealso::

           wreck.pep518_venvs.VenvMapLoader.ensure_abspath

        """
        ret = self._loader.project_base

        return ret

    def __repr__(self):
        """Display contents of VenvMap

        :returns: repr. Not useful for reproducing instance
        :rtype: str
        """
        cls_name = self.__class__.__name__

        # repr a list
        str_venvs = "["
        is_first = True
        for venv_req in self._venvs:
            if is_first:
                str_venvs += f"{venv_req!r}"
                is_first = False
            else:
                str_venvs += f", {venv_req!r}"
        str_venvs += "]"

        ret = (
            f"<{cls_name} "
            f"_loader={self._loader!r}, "
            f"_venvs={str_venvs}, "
            f"_missing={self._missing!r}"
            ">"
        )
        return ret

    def ensure_abspath(self, key):
        """Convenience wrapper around VenvMapLoader method of the same name.

        :param key: A relative or absolute path
        :type key: str | pathlib.Path
        :returns: Absolute path
        :rtype: pathlib.Path
        """
        ret = self._loader.ensure_abspath(key)
        return ret

    def __len__(self):
        """Number of virtual environments, **not** the requirements
        count for a particular venv.

        :returns: virtual environment count
        :rtype: int
        """
        return len(self._venvs)

    def __iter__(self):
        """Iterator of venv and respective requirements .in files

        Does not:

        - filter by venv
        - group by venv

        :returns: virtual environment count
        :rtype: typing_extensions.Self
        """
        return self

    def __next__(self):
        """Recreates the iterator everyone time it's completely consumed

        :returns: One mapping contains some paths and requirements Paths
        :rtype: wreck.pep518_venvs.VenvReq

        .. seealso::

           `reusable_range <https://realpython.com/python-iterators-iterables/#understanding-some-constraints-of-python-iterators>`_

        """
        try:
            return next(self._iter)
        except StopIteration:
            # Reinitialize iterator
            self._iter = iter(self._venvs)
            # signal end of iteration
            raise

    def __contains__(self, key):
        """Test if venv is known.

        :param key: a venv path
        :type key: typing.Any
        :returns: True if venv path known
        :rtype: bool
        """
        try:
            abspath_venv = self.ensure_abspath(key)
        except TypeError:
            ret = False
        else:
            is_found = False
            for venv_req in self._venvs:
                is_match = venv_req.venv_abspath == abspath_venv
                if is_match:
                    is_found = True
                else:  # pragma: no cover
                    pass
            ret = is_found

        return ret

    def __getitem__(self, key):
        """Get VenvReq from VenvMap. Either using an int or a slice.

        :param key: Which VenvReq(s) to get
        :type key: int | slice
        :returns: list of VenvReq or one VenvReq
        :rtype: list[wreck.pep518_venvs.VenvReq] | wreck.pep518_venvs.VenvReq
        :raises:

           - :py:exc:`TypeError` -- Unsupported type. Expect int or a slice
           - :py:exc:`IndexError` -- out of range

        """
        if isinstance(key, slice):
            # Get the start, stop, and step from the slice
            pin_count = len(self._venvs)
            ret = [self._venvs[ii] for ii in range(*key.indices(pin_count))]
        elif isinstance(key, int):
            # negative indices --> add len(self) until positive
            if key < 0:
                while key < 0:
                    key += len(self)

            if key >= len(self):
                msg_exc = f"The index ({key!s}) is out of range."
                raise IndexError(msg_exc)
            else:  # pragma: no cover
                pass

            ret = self._venvs[key]
        else:
            cls_name = type(self).__name__
            msg_exc = f"{cls_name} indices must be integers or slices, not {type(key)}"
            raise TypeError(msg_exc)

        return ret

    def reqs(self, key):
        """For one venv, get requirements (``.in``).

        :param key: venv relative or absolute path
        :type key: typing.Any
        :returns: One venv, VenvReq items
        :rtype: list[wreck.pep518_venvs.VenvReq]
        :raises:

           - :py:exc:`TypeError` -- venv relative path (as_posix) is a
             str key. Unsupported type

           - :py:exc:`KeyError` -- No such venv found

        """
        msg_exc_lookup = f"venv {key} not in [[tool.{TOML_SECTION_VENVS}]]"

        # Want both relpath and abspath
        try:
            abspath_key = self.ensure_abspath(key)
        except TypeError:
            raise
        path_cwd = self._loader.project_base
        relpath_key = abspath_key.relative_to(path_cwd)

        # Check if venv specified. May have no associated reqs
        t_venv_relpaths = self._loader.venv_relpaths
        is_venv_specified = relpath_key.as_posix() in t_venv_relpaths
        #    :code:`key not in self` removed
        if not is_venv_specified:
            #    venv not specified
            raise KeyError(msg_exc_lookup)
        else:  # pragma: no cover
            pass

        # no reqs, for this venv, is not a KeyError
        reqs = [
            venv_req for venv_req in self._venvs if venv_req.venv_abspath == abspath_key
        ]

        return reqs


def check_loader(loader):
    """Check loader valid

    :param loader: Should be a VenvMapLoader
    :type loader: typing.Any
    :raises:

        - :py:exc:`wreck.exceptions.MissingPackageBaseFolder` --
          loader not provided. Loader provides package base folder

    """
    is_loader_ng = loader is None or not isinstance(loader, VenvMapLoader)
    if is_loader_ng:
        msg_warn = "loader not provided. Loader provides package base folder"
        raise MissingPackageBaseFolder(msg_warn)
    else:  # pragma: no cover
        pass


def get_reqs(loader, venv_path=None, suffix_last=SUFFIX_IN):
    """get absolute path to requirement files

    Filtering by venv relative or absolute path is recommended

    :param loader: Contains some paths and loaded unparsed mappings
    :type loader: wreck.pep518_venvs.VenvMapLoader
    :param venv_path: Filter by venv relative or absolute path
    :type venv_path: typing.Any
    :param suffix_last: Default ``.in``. Last suffix is replaced, not all suffixes
    :type suffix_last: str
    :returns: Sequence of absolute path to requirements files
    :rtype: tuple[pathlib.Path]
    :raises:

       - :py:exc:`NotADirectoryError` -- venv relative paths do not correspond to
         actual venv folders

       - :py:exc:`ValueError` -- expecting [[tool.wreck.venvs]] field reqs to be a
         sequence

       - :py:exc:`KeyError` -- No such venv found

       - :py:exc:`wreck.exceptions.MissingRequirementsFoldersFiles` --
         There are missing ``.in`` files. Support file(s) not checked

       - :py:exc:`wreck.exceptions.MissingPackageBaseFolder` --
         loader invalid. Does not provide package base folder

    """
    # raises MissingPackageBaseFolder
    check_loader(loader)
    relpath_venv = check_venv_relpath(loader, venv_path)
    venv_relpath = relpath_venv.as_posix()

    # Sequence[str] | None
    check_suffixes = fix_check_suffixes(suffix_last)
    if check_suffixes is None:
        check_suffixes = (SUFFIX_IN,)
    else:  # pragma: no cover
        pass
    venv_relpaths = loader.venv_relpaths

    # Ensure requirements files defined in [[tool.wreck.venvs]] reqs exists
    try:
        venvs = VenvMap(
            loader,
            parse_venv_relpath=venv_relpath,
            check_suffixes=check_suffixes,
        )
        msg_missing = "\n".join(venvs.missing)
        is_missing = len(venvs.missing) != 0
        if is_missing:
            raise MissingRequirementsFoldersFiles(msg_missing)
        else:  # pragma: no cover
            pass
        assert len(venvs.missing) == 0, msg_missing
    except (NotADirectoryError, ValueError, AssertionError):
        raise

    set_out = set()
    is_get_all = venv_relpath is None
    is_venvs_found = venv_relpath is not None and venv_relpath in venv_relpaths
    if is_get_all or is_venvs_found:
        venv_relpaths_filtered = [
            venv_path_key
            for venv_path_key in venv_relpaths
            if is_get_all or venv_path_key == venv_relpath
        ]
        for venv_path_key in venv_relpaths_filtered:
            # filtered so no KeyError
            reqs = venvs.reqs(venv_path_key)

            for path_in_ in reqs:
                # requirements .unlock files, not the source within .in files
                # where to apply ``nudges`` is another story.
                path_venvreq = cast(
                    "Path",
                    resolve_joinpath(path_in_.project_base, path_in_.req_relpath),
                )
                abspath_req = replace_suffixes_last(path_venvreq, suffix_last)
                set_out.add(abspath_req)
    else:
        # venv_path not in venv_relpaths
        msg_warn = (
            f"venv {venv_relpath} not in [[tool.{TOML_SECTION_VENVS}]] "
            f"venv paths {venv_relpaths}"
        )
        raise KeyError(msg_warn)

    ret = tuple(set_out)

    return ret


def fix_check_suffixes(check_suffixes):
    """Passthrough a Sequence[str]. Coerce str into a non str Sequence.
    If unsupported type or None return None

    :param check_suffixes: Should be a Sequence[str] or a str
    :type check_suffixes: typing.Any
    :returns: A non-str Sequence or None if unsupported type
    :rtype: collections.abc.Sequence[str] | None
    """

    def is_nonstr_sequence(val):
        """Check if a Sequence but not a str
        :param val:
        :type val: typing.Any
        :returns: True is Sequence but not a str
        :rtype: bool
        """
        ret = val is not None and isinstance(val, Sequence) and not isinstance(val, str)
        return ret

    is_seq_str = (
        check_suffixes is not None
        and isinstance(check_suffixes, Sequence)
        and isinstance(check_suffixes, str)
    )

    if is_seq_str:
        check_suffixes_local = (check_suffixes,)
    elif is_nonstr_sequence(check_suffixes):
        check_suffixes_local = check_suffixes
    else:
        # unsupported type, but not dealt with here
        check_suffixes_local = None
    return check_suffixes_local
