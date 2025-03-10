"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

.. py:data:: is_module_debug
   :type: bool

   Switch on/off module level debugging

.. py:data:: _logger
   :type: logging.Logger

   Module level logger

.. py:data:: __all__
   :type: tuple[str]
   :value: ("Fixing",)

   Module exports

"""

import logging
import os
from collections.abc import Sequence
from typing import TYPE_CHECKING

from packaging.specifiers import InvalidSpecifier

from .check_type import is_ok
from .constants import (
    SUFFIX_LOCKED,
    SUFFIX_UNLOCKED,
    g_app_name,
)
from .exceptions import (
    ArbitraryEqualityNotImplemented,
    MissingRequirementsFoldersFiles,
    PinMoreThanTwoSpecifiers,
)
from .lock_collections import Ins
from .lock_datum import (
    OutLastSuffix,
    PinDatum,
)
from .lock_discrepancy import (
    Resolvable,
    ResolvedMsg,
    UnResolvable,
    filter_acceptable,
    get_ss_set,
    get_the_fixes,
    has_discrepancies_version,
    write_to_file_nudge_pin,
)
from .lock_util import (
    is_shared,
    replace_suffixes_last,
)
from .pep518_venvs import (
    VenvMap,
    VenvMapLoader,
    check_loader,
)

if TYPE_CHECKING:
    from .lock_datum import DatumByPkg
    from .lock_discrepancy import PkgsWithIssues

is_module_debug = True
_logger = logging.getLogger(f"{g_app_name}.lock_fixing")

__all__ = ("Fixing",)


class OutMessages:
    """Per Out file holds three message lists

    - unresolvables

    - fixed (issues)

    - shared

    Create two instances. One for each output file type. OutLastSuffix.UNLOCK
    will not have unresolvables messages

    .. py:attribute:: __slots__
       :type: tuple[str, str, str, str]
       :value: ("_last_suffix", "_unresolvables", "_fixed_issues", \
       "_resolvable_shared")

       Slightly smaller footprint in terms of memory efficiency

    :raises:

       - :py:exc:`AssertionError` -- Unsupported output file last suffix

    """

    __slots__ = (
        "_last_suffix",
        "_unresolvables",
        "_fixed_issues",
        "_resolvable_shared",
    )

    def __init__(self, last_suffix: OutLastSuffix):
        """Class constructor"""
        assert isinstance(last_suffix, OutLastSuffix)
        self._last_suffix = last_suffix
        # Initialize message lists
        self._unresolvables = []
        self._fixed_issues = []
        self._resolvable_shared = []

    def append(self, item, last_suffix=OutLastSuffix.LOCK):
        """Append out message.

        OutLastSuffix must match, so can use haphazardly

        :param item: An out message. Currently there are three out message types
        :type item: typing.Any
        :param last_suffix:

           Out file type characterized by last suffix, not properties like .shared

        :type last_suffix: wreck.datum.OutLastSuffix
        """
        is_type_match = (
            last_suffix is not None
            and isinstance(last_suffix, OutLastSuffix)
            and last_suffix == self._last_suffix
        )
        is_item_ok = item is not None
        if is_type_match and is_item_ok:
            if isinstance(item, UnResolvable):
                # Only applies to .lock files.
                self._unresolvables.append(item)
            elif isinstance(item, ResolvedMsg):
                # Fixed or other messages
                self._fixed_issues.append(item)
            elif (
                isinstance(item, Sequence)
                and not isinstance(item, str)
                and len(item) == 3
            ):
                # tuple[str, wreck.lock_discrepancy.Resolvable, wreck.lock_datum.PinDatum]
                self._resolvable_shared.append(item)
            else:  # pragma: no cover
                # non-None Unsupported item
                pass
        else:
            # Unsupported
            pass

    def extend(self, items, last_suffix=OutLastSuffix.LOCK):
        """Append many items

        :param items: Normally a sequence of supported item
        :type items: typing.Any
        :param last_suffix:

           Out file type characterized by last suffix, not properties like .shared

        :type last_suffix: wreck.datum.OutLastSuffix
        """
        if (
            items is not None
            and isinstance(items, Sequence)
            and not isinstance(items, str)
        ):
            for item in items:
                self.append(item, last_suffix=last_suffix)
            else:  # pragma: no cover
                pass
        else:  # pragma: no cover
            pass

    @property
    def resolvable_shared(self):
        """``.shared.in`` do not try to resolve.

        :returns: list of Resolvable issues
        :rtype: list[tuple[str, wreck.lock_discrepancy.Resolvable, wreck.lock_datum.PinDatum]]
        """
        ret = self._resolvable_shared

        return ret

    @property
    def unresolvables(self):
        """Get unresolvable issues

        :returns: list of unresolvable issues
        :rtype: list[wreck.lock_discrepancy.UnResolvable]
        """
        ret = self._unresolvables

        return ret

    @property
    def fixed_issues(self):
        """Get fixed issue messages

        :returns: list of fixed issues
        :rtype: list[wreck.lock_discrepancy.ResolvedMsg]
        """
        ret = self._fixed_issues

        return ret

    @property
    def has_unresolvables(self) -> bool:
        """Check if any unresolvables, if so will need to skip creating .unlock file

        :returns: True if there are unresolvables
        :rtype: bool
        """
        ret = len(self._unresolvables) != 0

        return ret


def _check_is_dry_run(is_dry_run, default=False):
    """Coerce into a bool. Might not be possible to support feature is_dry_run

    :param is_dry_run: Dry run would ideally not write to disk
    :type is_dry_run: typing.Any
    :param default: Normally is_dry_run default is False
    :type default: bool
    :returns: False if is_dry_run is anything besides a bool and True
    :rtype: bool
    """
    is_dry_run_ng = is_dry_run is None or not isinstance(is_dry_run, bool)
    if is_dry_run_ng:
        ret = default
    else:
        ret = is_dry_run

    return ret


def _get_qualifiers(d_subset):
    """Given package name, choose qualifiers

    :param d_subset: key is package name value is set of datum
    :type d_subset: wreck.lock_datum.DatumByPkg
    :returns: dict of package name and qualifiers joined into one str
    :rtype: dict[str, str]
    """
    d_pkg_qualifiers = {}
    for pkg_name, pindatum_in in d_subset.items():
        for pin in pindatum_in:
            # Does this pin have qualifiers?
            quals = pin.qualifiers
            has_quals = len(quals) != 0
            if pkg_name not in d_pkg_qualifiers.keys() and has_quals:
                str_pkg_qualifiers = "; ".join(quals)
                str_pkg_qualifiers = f"; {str_pkg_qualifiers}"
                d_pkg_qualifiers[pkg_name] = str_pkg_qualifiers
            else:  # pragma: no cover
                pass

        # empty str for a package without qualifiers
        if pkg_name not in d_pkg_qualifiers.keys():
            d_pkg_qualifiers[pkg_name] = ""
        else:  # pragma: no cover
            pass

    return d_pkg_qualifiers


def _load_once(
    ins,
    locks,
    venv_relpath,
):
    """Cache .in and .lock files

    :param ins: Collection of FilePins. ``.in`` files
    :type ins: wreck.lock_collections.Ins
    :param locks: Collection of FilePins.  ``.lock`` files
    :type locks: wreck.lock_collections.Ins
    :param venv_relpath: venv relative path
    :type venv_relpath: str
    :returns: list of resolvables and list of unresolvables
    :rtype: tuple[list[wreck.lock_discrepancy.Resolvable], list[wreck.lock_discrepancy.UnResolvable]]
    """
    if TYPE_CHECKING:
        d_subset_notables: DatumByPkg
        d_subset_all_in: DatumByPkg
        d_subset_all_lock: DatumByPkg
        locks_pkg_by_versions: PkgsWithIssues
        locks_by_pkg_w_issues: DatumByPkg
        d_qualifiers_in: dict[str, str]
        d_qualifiers_lock: dict[str, str]
        set_datum: set[PinDatum]

    dotted_path = f"{g_app_name}.lock_fixing._load_once"
    """REMOVE duplicates from same requirements file.
    Use ``dict[str, set[PinDatum]]``, not a ``dict[str, list[PinDatum]]``
    Mimics Pins._wrapper_pins_by_pkg
    """
    # Group notable locks (PinDatum) by pkg_name --> PinsByPkg
    d_subset_notables = {}
    gen_fpins_zeroes = ins.zeroes
    for fpin_zero in gen_fpins_zeroes:
        for pindatum_lock_notable in fpin_zero.by_pin_or_qualifier():
            pkg_name = pindatum_lock_notable.pkg_name
            is_not_in = pkg_name not in d_subset_notables.keys()
            if is_not_in:
                # add first PinDatum
                set_new = set()
                set_new.add(pindatum_lock_notable)
                d_subset_notables.update({pkg_name: set_new})
            else:
                set_pindatums = d_subset_notables[pkg_name]
                set_pindatums.add(pindatum_lock_notable)
                d_subset_notables.update({pkg_name: set_pindatums})

    # Group all ins (PinDatum) by pkg_name
    d_subset_all_in = {}
    gen_fpins_zeroes = ins.zeroes
    for fpin_zero in gen_fpins_zeroes:
        # From FilePins --> list[PinDatum]
        for pindatum_lock in fpin_zero._pins:
            pkg_name = pindatum_lock.pkg_name
            is_not_in = pkg_name not in d_subset_all_in.keys()
            if is_not_in:
                # add first PinDatum
                set_new = set()
                set_new.add(pindatum_lock)
                d_subset_all_in.update({pkg_name: set_new})
            else:
                set_pindatums = d_subset_all_in[pkg_name]
                set_pindatums.add(pindatum_lock)
                d_subset_all_in.update({pkg_name: set_pindatums})

    """ Group all locks (PinDatum) by pkg_name
    ONLY LOCK CAN CORRECTLY IDENTIFY ALL PACKAGES
    """
    d_subset_all_lock = {}
    gen_fpins_zeroes = locks._file_pins
    for fpin_zero in gen_fpins_zeroes:
        # From FilePins --> list[PinDatum]
        for pindatum_lock in fpin_zero._pins:
            pkg_name = pindatum_lock.pkg_name
            is_not_in = pkg_name not in d_subset_all_lock.keys()
            if is_not_in:
                # add first PinDatum
                set_new = set()
                set_new.add(pindatum_lock)
                d_subset_all_lock.update({pkg_name: set_new})
            else:
                set_pindatums = d_subset_all_lock[pkg_name]
                set_pindatums.add(pindatum_lock)
                d_subset_all_lock.update({pkg_name: set_pindatums})

    """In .lock files search for version discrepancies
    See Pins.by_pkg_with_issues
    """
    locks_pkg_by_versions = has_discrepancies_version(d_subset_all_lock)

    """filter out packages without issues

    locks_pkg_by_versions contains all .lock package issues
    Search thru the resolved .in, but still will contain less packages"""
    locks_by_pkg_w_issues = {
        k: v for k, v in d_subset_notables.items() if k in locks_pkg_by_versions.keys()
    }

    """Pure ``.lock`` version discrepancies. Dependency not found
    in ``.in``. Need to be fix in ``.lock`` files"""
    locks_by_pkg_w_issues_remaining = {
        k: v
        for k, v in d_subset_all_lock.items()
        if k in locks_pkg_by_versions.keys() and k not in locks_by_pkg_w_issues.keys()
    }

    # get_issues --> Pins.qualifiers_by_pkg
    #    From d_subset_notables (filtered .in files)
    d_qualifiers_in = _get_qualifiers(d_subset_notables)

    # from .lock file, get package qualifiers (dict key, pkg_name)
    d_qualifiers_lock = _get_qualifiers(d_subset_all_lock)

    unresolvables = []
    resolvables = []

    # get_issues -- no corresponding pin in .in file
    # Pure .lock package dependency conflict
    for pkg_name, set_datum in locks_by_pkg_w_issues_remaining.items():
        str_pkg_qualifiers = d_qualifiers_lock[pkg_name]

        # Choose highest
        highest = locks_pkg_by_versions[pkg_name]["highest"]
        #    N/A only dealing with .lock files
        nudge_pin_unlock = f"{pkg_name}>={highest!s}"
        nudge_pin_lock = f"{pkg_name}=={highest!s}"

        msg_warn = (
            f"{dotted_path} .lock files conflict. "
            f"During .unlock fix, will add nudge pin {nudge_pin_unlock}"
        )
        _logger.warning(msg_warn)

        resolvables.append(
            Resolvable(
                venv_relpath,
                pkg_name,
                str_pkg_qualifiers,
                nudge_pin_unlock,
                nudge_pin_lock,
            )
        )

    # get_issues -- corresponding pin in .in file
    for pkg_name, set_datum in locks_by_pkg_w_issues.items():
        # Without filtering, get qualifiers from .in files
        str_pkg_qualifiers = d_qualifiers_in.get(pkg_name, "")
        # Pins.filter_pins_of_pkg
        #     nudge_pins must come from .in
        set_pindatum = d_subset_all_in[pkg_name]
        highest = locks_pkg_by_versions[pkg_name]["highest"]
        others = locks_pkg_by_versions[pkg_name]["others"]

        # DRY. Needed when UnResolvable
        try:
            set_ss = get_ss_set(set_pindatum)
        except InvalidSpecifier:
            # nonsense version identifier e.g. ``~~24.2``
            set_ss = set()
            unresolvables.append(
                UnResolvable(
                    venv_relpath,
                    pkg_name,
                    str_pkg_qualifiers,
                    set_ss,
                    highest,
                    others,
                    set_pindatum,
                )
            )
            continue

        is_ss_count_zero = len(set_ss) == 0

        t_acceptable = filter_acceptable(
            set_pindatum,
            set_ss,
            highest,
            others,
        )
        set_acceptable, lsts_specifiers, is_eq_affinity_value = t_acceptable

        try:
            t_chosen = get_the_fixes(
                set_acceptable,
                lsts_specifiers,
                highest,
                is_eq_affinity_value,
                is_ss_count_zero,
            )
        except (ArbitraryEqualityNotImplemented, PinMoreThanTwoSpecifiers):
            # unresolvable conflict --> warning
            unresolvables.append(
                UnResolvable(
                    venv_relpath,
                    pkg_name,
                    str_pkg_qualifiers,
                    set_ss,
                    highest,
                    others,
                    set_pindatum,
                )
            )
            continue

        assert isinstance(t_chosen, tuple)
        lock_nudge_pin, unlock_nudge_pin, is_found = t_chosen

        if not is_found:
            # unresolvable conflict --> warning
            unresolvables.append(
                UnResolvable(
                    venv_relpath,
                    pkg_name,
                    str_pkg_qualifiers,
                    set_ss,
                    highest,
                    others,
                    set_pindatum,
                )
            )
        else:
            # resolvable
            nudge_pin_unlock = f"{pkg_name}{unlock_nudge_pin}"
            nudge_pin_lock = f"{pkg_name}{lock_nudge_pin}"

            msg_warn = (
                f"{dotted_path} resolvable conflict. "
                f"During .unlock fix, will add nudge pin {nudge_pin_unlock}"
            )
            _logger.warning(msg_warn)

            resolvables.append(
                Resolvable(
                    venv_relpath,
                    pkg_name,
                    str_pkg_qualifiers,
                    nudge_pin_unlock,
                    nudge_pin_lock,
                )
            )

    t_ret = resolvables, unresolvables

    return t_ret


def _fix_resolvables(
    resolvables,
    locks: Ins,
    venv_relpath,
    is_dry_run=False,
    suffixes=(SUFFIX_LOCKED,),
):
    """Go thru resolvables and fix affected ``.unlock`` and ``.lock`` files

    Assumes target requirements file exists and is a file. This is a post processor. After
    .in, .unlock, and .lock files have been created.

    :param resolvables:

       Unordered list of Resolvable. Use to fix ``.unlock`` and ``.lock`` files

    :type resolvables: collections.abc.Sequence[wreck.lock_datum.Resolvable]
    :param locks: .lock file PinDatum collection
    :type locks: wreck.lock_collections.Ins
    :param venv_relpath: venv relative path
    :type venv_relpath: str
    :param is_dry_run:

       Default False. Should be a bool. Do not make changes. Merely
       report what would have been changed

    :type is_dry_run: typing.Any | None
    :param suffixes:

       Default ``(".lock",)``. Suffixes to process, in order

    :type suffixes: tuple[typing.Literal[wreck.constants.SUFFIX_LOCKED] | typing.Literal[wreck.constants.SUFFIX_UNLOCKED]]
    :returns:

       Wrote messages. For shared, tuple of suffix, resolvable, and Pin (of .lock file).
       This is why the suffix is provided and first within the tuple

    :rtype: tuple[list[wreck.lock_discrepancy.ResolvedMsg], list[tuple[str, str, wreck.lock_discrepancy.Resolvable, wreck.lock_datum.PinDatum]]]
    :raises:

       - :py:exc:`wreck.exceptions.MissingRequirementsFoldersFiles` --
         one or more requirements files is missing

    """
    if TYPE_CHECKING:
        fixed_issues: list[ResolvedMsg]
        applies_to_shared: list[tuple[str, str, Resolvable, PinDatum]]

    is_dry_run = _check_is_dry_run(is_dry_run)

    if suffixes is None or not (
        SUFFIX_LOCKED in suffixes or SUFFIX_UNLOCKED in suffixes
    ):
        # Query all requirements . Do both, but first, ``.lock``
        suffixes = (SUFFIX_LOCKED,)
    else:  # pragma: no cover
        pass

    fixed_issues = []
    applies_to_shared = []

    # gen_fpins_zeroes = locks._file_pins
    for fpin_zero in locks:
        # From FilePins --> list[PinDatum]
        for pindatum_lock in fpin_zero._pins:
            pkg_name = pindatum_lock.pkg_name
            is_shared_type = is_shared(pindatum_lock.file_abspath.name)
            for resolvable in resolvables:
                is_match = pkg_name == resolvable.pkg_name
                if not is_match:  # pragma: no cover
                    pass
                else:
                    for suffix in suffixes:
                        # In ``suffixes`` tuple, lock is first entry
                        is_lock = suffix == SUFFIX_LOCKED
                        if is_lock:
                            path_f = pindatum_lock.file_abspath
                        else:
                            path_f = replace_suffixes_last(
                                pindatum_lock.file_abspath,
                                SUFFIX_UNLOCKED,
                            )

                        if is_shared_type:
                            """``.shared.*`` files affect multiple venv.
                            Nudge pin takes into account one venv. Inform
                            the human"""
                            if is_lock:
                                # One entry rather than two.
                                # Implied affects both .unlock and .lock
                                t_four = (
                                    venv_relpath,
                                    suffix,
                                    resolvable,
                                    pindatum_lock,
                                )
                                applies_to_shared.append(t_four)
                            else:  # pragma: no cover
                                pass
                        else:
                            # remove any line dealing with this package
                            # append resolvable.nudge_unlock
                            if is_lock:
                                nudge = resolvable.nudge_lock
                            else:
                                nudge = resolvable.nudge_unlock

                            if nudge is not None:
                                nudge_pin_line = (
                                    f"{nudge}{resolvable.qualifiers}{os.linesep}"
                                )

                                if not is_dry_run:
                                    write_to_file_nudge_pin(
                                        path_f, pindatum_lock.pkg_name, nudge_pin_line
                                    )
                                else:
                                    pass

                                # Report resolved dependency conflict
                                msg_fixed = ResolvedMsg(
                                    venv_relpath, path_f, nudge_pin_line.rstrip()
                                )
                                fixed_issues.append(msg_fixed)
                            else:  # pragma: no cover
                                msg_warn = (
                                    f"{path_f} {pindatum_lock.pkg_name} is_lock "
                                    f"{is_lock} nudge {nudge}{resolvable.qualifiers}"
                                )
                                _logger.warning(msg_warn)

    return fixed_issues, applies_to_shared


class Fixing:
    """Fix ``.lock`` files using only ``.in`` files. Assume ``.unlock``
    do not exist or are wrong.

    :raises:

       - :py:exc:`TypeError` -- unsupported type for venv_relpath expects str

       - :py:exc:`NotADirectoryError` -- there is no corresponding venv folder. Create it

       - :py:exc:`ValueError` -- expecting [[tool.wreck.venvs]] field reqs should be a
         list of relative path without .in .unlock or .lock suffix

       - :py:exc:`wreck.exceptions.MissingRequirementsFoldersFiles` --
         there are unresolvable constraint(s)

    """

    _ins: Ins
    _locks: Ins
    _venv_relpath: str
    _loader: VenvMapLoader
    _out_lock_messages: OutMessages
    _out_unlock_messages: OutMessages

    def __init__(self, loader, venv_relpath, out_lock_messages, out_unlock_messages):
        """Class constructor"""
        meth_dotted_path = f"{g_app_name}.lock_fixing.Fixing.__init__"

        # may raise MissingPackageBaseFolder
        check_loader(loader)

        if not is_ok(venv_relpath):
            msg_warn = (
                f"{meth_dotted_path} unsupported type for venv_relpath expects str"
            )
            raise TypeError(msg_warn)
        else:  # pragma: no cover
            pass

        try:
            VenvMap(loader)
        except (NotADirectoryError, ValueError):
            raise

        self._loader = loader
        self._venv_relpath = venv_relpath

        if is_module_debug:  # pragma: no cover
            msg_info = f"{meth_dotted_path} loader.project_base {loader.project_base}"
            _logger.info(msg_info)
        else:  # pragma: no cover
            pass

        self._out_lock_messages = out_lock_messages
        self._out_unlock_messages = out_unlock_messages

        # Store ``.in`` files ONCE. Auto resolution loop occurs
        try:
            ins = Ins(loader, venv_relpath)

            """ins.load() split into three methods:
            ins._load_filepins, ins._check_top_level, and ins._load_resolution_loop"""
            ins._load_filepins()

            # Check .in includes contain any .lock files
            lst_issues = ins._check_top_level()
            for t_three in lst_issues:
                item = ResolvedMsg(*t_three)
                self._out_unlock_messages.append(item, last_suffix=OutLastSuffix.UNLOCK)

            ins._load_resolution_loop()

            self._ins = ins

            # Store ``.lock`` files ONCE
            locks = Ins(loader, venv_relpath)
            locks.load(suffix_last=SUFFIX_LOCKED)
            self._locks = locks
        except MissingRequirementsFoldersFiles:
            raise

    @staticmethod
    def fix_requirements_lock(loader, venv_relpath, is_dry_run=False):
        """Factory that supplied OutMessages for both .lock and .unlock files

        Iterate thru venv. ``.unlock`` may not yet exist. For each
        ``.in`` file, resolution loop once

        :param loader: Contains some paths and loaded unparsed mappings
        :type loader: wreck.pep518_venvs.VenvMapLoader
        :param venv_relpath: venv relative path is a key. To choose a tools.wreck.venvs.req
        :type venv_relpath: str
        :param is_dry_run:

           Default False. Should be a bool. Do not make changes. Merely
           report what would have been changed

        :type is_dry_run: typing.Any | None
        :returns:

           list contains tuples. venv path, resolves messages, unresolvable
           issues, resolvable3 issues dealing with .shared requirements file

        :rtype: wreck.lock_fixing.Fixing
        :raises:

           - :py:exc:`NotADirectoryError` -- there is no corresponding venv folder. Create it

           - :py:exc:`ValueError` -- expecting [[tool.wreck.venvs]] field reqs should be a
             list of relative path without .in .unlock or .lock suffix

           - :py:exc:`wreck.exceptions.MissingRequirementsFoldersFiles` --
             missing constraints or requirements files or folders

           - :py:exc:`wreck.exceptions.MissingPackageBaseFolder` --
             Invalid loader. Does not provide package base folder

           - :py:exc:`TypeError` -- venv relpath is None or unsupported type

        """
        # may raise MissingPackageBaseFolder
        check_loader(loader)

        is_dry_run = _check_is_dry_run(is_dry_run)

        out_lock_messages = OutMessages(last_suffix=OutLastSuffix.LOCK)
        out_unlock_messages = OutMessages(last_suffix=OutLastSuffix.UNLOCK)

        try:
            fixing = Fixing(
                loader, venv_relpath, out_lock_messages, out_unlock_messages
            )
        except (
            NotADirectoryError,
            ValueError,
            MissingRequirementsFoldersFiles,
            TypeError,
        ):
            raise

        fixing.get_issues()
        fixing.fix_resolvables(is_dry_run=is_dry_run)
        fixing.fix_unlock(is_dry_run=is_dry_run)

        return fixing

    def fix_unlock(self, is_dry_run=False):
        """Create ``.unlock`` files then fix using knowledge gleened while
        creating and fixing ``.lock`` files

        :param is_dry_run: Default False. True to avoid writing to file
        :type is_dry_run: bool
        """
        dotted_path = f"{g_app_name}.lock_fixing.Fixing.fix_unlock"
        is_dry_run = _check_is_dry_run(is_dry_run)

        # has_unresolvables = len(self._unresolvables) != 0
        has_unresolvables = self._out_lock_messages.has_unresolvables
        if has_unresolvables:
            msg_warn = (
                f"{dotted_path} There are unresolved issues. Create "
                ".unlock files ... skip"
            )
            _logger.warning(msg_warn)
        else:
            # Create .unlock files
            gen = self._ins.write()
            #    execute generator. Returns list[abspath]
            list(gen)

            # Fix .unlock files using info from .lock
            fixed_issues, applies_to_shared = _fix_resolvables(
                self._resolvables,
                self._locks,
                self._venv_relpath,
                is_dry_run=is_dry_run,
                suffixes=(SUFFIX_UNLOCKED,),
            )

            # Save unlock messages
            self._out_unlock_messages.extend(fixed_issues)
            self._out_unlock_messages.extend(applies_to_shared)

    def get_issues(self):
        """Identify resolvable and unresolvable issues.

        :returns: lists of resolvable and unresolvable issues
        :rtype: tuple[list[wreck.lock_discrepancy.Resolvable], list[wreck.lock_discrepancy.UnResolvable]]
        """
        ret = _load_once(self._ins, self._locks, self._venv_relpath)
        self._resolvables = ret[0]
        # self._unresolvables = ret[1]
        self._out_lock_messages.extend(ret[1])

    def fix_resolvables(self, is_dry_run=False):
        """Resolve the resolvable dependency conflicts. Refrain from attempting to
        fix resolvable conflicts involving .shared requirements files.

        :param is_dry_run: Default False. True to avoid writing to file
        :type is_dry_run: bool
        """
        is_dry_run = _check_is_dry_run(is_dry_run)

        t_results = _fix_resolvables(
            self._resolvables,
            self._locks,
            self._venv_relpath,
            is_dry_run=is_dry_run,
        )
        fixed_issues, applies_to_shared = t_results
        # self._fixed_issues = fixed_issues
        self._out_lock_messages.extend(fixed_issues)

        # group by venv -- resolvable .shared
        #     venv_path, suffix (.unlock or .lock), resolvable, pin
        for t_resolvable_shared in applies_to_shared:
            resolvable_shared_without_venv_path = t_resolvable_shared[1:]
            self._out_lock_messages.append(resolvable_shared_without_venv_path)

    @property
    def resolvables(self):
        """Get resolvable issues

        :returns: list of Resolvable issues
        :rtype: list[wreck.lock_discrepancy.Resolvable]
        """
        ret = self._resolvables

        return ret
