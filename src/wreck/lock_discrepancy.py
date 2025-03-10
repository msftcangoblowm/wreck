"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

.. py:class:: PkgsWithIssues

.. py:data:: PkgsWithIssues
   :type: dict[str, dict[str, packaging.version.Version | set[packaging.version.Version]]]
   :noindex:

   Packages by a dict containing highest version and other versions

.. py:data:: __all__
   :type: tuple[str, str, str, str, str, str, str, str, str]
   :value: ("PkgsWithIssues", "Resolvable", "ResolvedMsg", "UnResolvable", \
   "get_ss_set", "filter_acceptable", "has_discrepancies_version", \
   "get_the_fixes", "write_to_file_nudge_pin")

   Module exports

.. py:data:: is_module_debug
   :type: bool
   :value: False

   Flag to turn on module level logging. Should be off in production

.. py:data:: _logger
   :type: logging.Logger

   Module level logger

"""

from __future__ import annotations

import io
import logging
import operator
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Union,
    cast,
)

from packaging.specifiers import (
    InvalidSpecifier,
    SpecifierSet,
)
from packaging.version import Version

from .constants import g_app_name
from .exceptions import (
    ArbitraryEqualityNotImplemented,
    PinMoreThanTwoSpecifiers,
)
from .lock_datum import (
    DatumByPkg,
    PinDatum,
    pprint_pins,
)

if sys.version_info >= (3, 10):  # pragma: no cover py-gte-310-else
    DC_SLOTS = {"slots": True}
else:  # pragma: no cover py-gte-310
    DC_SLOTS = {}

is_module_debug = True
_logger = logging.getLogger(f"{g_app_name}.lock_discrepancy")

__all__ = (
    "PkgsWithIssues",
    "Resolvable",
    "ResolvedMsg",
    "UnResolvable",
    "filter_acceptable",
    "get_ss_set",
    "has_discrepancies_version",
    "get_the_fixes",
    "write_to_file_nudge_pin",
)

PkgsWithIssues = dict[str, dict[str, Union[Version, set[Version]]]]


def _specifier_length(specifier):
    """Determine length of operator within specifier

    :param specifier: Format ``[operator][version]``
    :type specifier: str
    :returns: Operator str length
    :rtype: int
    :raises:

       - :py:exc:`ValueError` -- Unknown specifier

    """
    t_len_1 = ("<", ">")
    t_len_2 = ("<=", ">=", "~=", "==", "!=")
    t_len_3 = "==="
    t_negatives = ("!==",)
    if specifier.startswith(t_len_3):
        # === arbitrary equality
        # https://peps.python.org/pep-0440/#arbitrary-equality
        specifier_len = 3
    elif specifier.startswith(t_len_2) and not specifier.startswith(t_negatives):
        specifier_len = 2
    elif specifier.startswith(t_len_1) and not specifier.startswith(t_negatives):
        specifier_len = 1
    else:
        msg_warn = f"Unknown specifier {specifier!r}"
        raise ValueError(msg_warn)

    return specifier_len


def has_discrepancies_version(d_by_pkg: DatumByPkg):
    """Across ``.lock`` files, packages with discrepancies.

    Comparison limited to equality

    :param d_by_pkg: Within one venv, all lock packages' ``set[PinDatum]``
    :type d_by_pkg: wreck.lock_datum.DatumByPkg
    :returns:

       pkg name / highest version. Only packages with discrepancies.
       With the highest version, know which version to *nudge* to.

    :rtype: wreck.lock_discrepancy.PkgsWithIssues
    """
    if TYPE_CHECKING:
        d_out: PkgsWithIssues
        pkg_name: str
        highest: Version | None

    d_out = {}
    for pkg_name, pins in d_by_pkg.items():
        # pick latest version
        highest = None
        set_others = set()
        has_changed = False
        for pin in pins:
            """Get version. Since a ``.lock`` file, there will only be one
            specifier ``==[sem version]``"""
            specifier = pin.specifiers[0]
            specifier_len = _specifier_length(specifier)
            pkg_sem_version = specifier[specifier_len:]
            ver = Version(pkg_sem_version)

            if highest is None:
                highest = ver
            else:
                is_greater = ver > highest
                is_not_eq = ver != highest

                if is_greater:
                    set_others.add(highest)
                    set_others.discard(ver)
                    highest = ver
                    has_changed = True
                elif is_not_eq:
                    # lower indicates discrepancy exists.
                    # Keep lowers to have available versions set
                    set_others.add(ver)
                    has_changed = True
                else:  # pragma: no cover
                    pass

        if has_changed:
            d_out[pkg_name] = {
                "highest": cast("Version", highest),
                "others": cast("set[Version]", set_others),
            }
        else:  # pragma: no cover
            # continue
            pass

    return d_out


def get_ss_set(set_pindatum):
    """Create a set of all SpecifierSet

    :param set_pindatum: PinDatum for the same package, from all ``.lock`` files
    :type set_pindatum: set[wreck.lock_datum.PinDatum]
    :returns: set of SpecifierSet
    :rtype: set[packaging.specifiers.SpecifierSet]

    :raises:

        - :py:exc:`packaging.specifiers.InvalidSpecifier` -- In
          SpecifierSet unsupported operator

    """
    set_ss = set()
    try:
        for pin in set_pindatum:
            # ss_pre = SpecifierSet(",".join(pin.specifiers), prereleases=True)
            ss_release = SpecifierSet(",".join(pin.specifiers))
            set_ss.add(ss_release)
    except InvalidSpecifier:
        raise

    # An empty SpecifierSet is worthless and annoying cuz throws off count
    ss_empty = SpecifierSet("")
    if ss_empty in set_ss:
        set_ss.discard(ss_empty)
    else:  # pragma: no cover
        pass

    return set_ss


def _get_specifiers(set_pindatum):
    """Get specifiers from pins

    :param set_pindatum: PinDatum for the same package, from all ``.lock`` files
    :type set_pindatum: set[wreck.lock_datum.PinDatum]
    :return: Specifiers lists
    :rtype: list[list[str]]
    """
    lst = []
    for pin in set_pindatum:
        lst.append(pin.specifiers)

    return lst


def _parse_specifiers(specifiers):
    """Extract specifers, operator and version ignore ``!=`` specifiers.

    :param specifiers:

       .unlock or .lock file line. Has package name, but might not be exact

    :type specifiers: list[str]
    :returns: original specifiers list replace str with a tuple of it's parts
    :rtype: str | None

    .. seealso::

       :pep:`440`

       :py:func:`escape characters <re.escape>`


    """
    dotted_path = f"{g_app_name}.lock_discrepancy._parse_specifiers"
    # Assume does not contain comma separators
    pattern = r"^(\s)*(===|==|<=|>=|<|>|~=|!=)(\S+)"

    lst = []
    for spec in specifiers:
        m = re.match(pattern, spec)
        if m is None:  # pragma: no cover
            if is_module_debug:
                msg_info = f"{dotted_path} failed to parse pkg from spec: {spec!r}"
                _logger.info(msg_info)
            else:
                pass
            continue
        else:
            groups = m.groups(default=None)  # noqa: F841
            oper = groups[1]
            oper = oper.strip()
            ver = groups[2]
            ver = ver.strip()
            t_parsed = (oper, ver)
            lst.append(t_parsed)

    return lst


def nudge_pin_unlock_v1(str_operator, found):
    """Assumes found is not None aka unresolvable.

    Will later need to prepend pkg_name

    :param str_operator: Operator
    :type str_operator: str
    :param str_operator: Semantic version
    :type str_operator: packaging.version.Version
    :returns: unlock nudge pin
    :rtype: str
    """
    nudge_pin_unlock = f"{str_operator}{found!s}"
    return nudge_pin_unlock


def nudge_pin_lock_v1(found):
    """Assumes found is not None aka unresolvable

    Will later need to prepend pkg_name

    :param str_operator: Semantic version
    :type str_operator: packaging.version.Version
    :returns: lock nudge pin
    :rtype: str
    """
    nudge_pin_lock = f"=={found!s}"

    return nudge_pin_lock


def filter_acceptable(
    set_pindatum,
    set_ss,
    highest,
    others,
):
    """:py:class:`~packaging.specifiers.SpecifierSet` does the heavy
    lifting, filtering out unacceptable possibilities

    :py:meth:`~wreck.lock_discrepancy.get_ss_set` has already filtered invalid operators

    :param set_pindatum: PinDatum for the same package, from all ``.lock`` files
    :type set_pindatum: set[wreck.lock_datum.PinDatum]
    :param set_ss: set of all SpecifierSet
    :type set_ss: set[packaging.specifiers.SpecifierSet]
    :param highest: Highest Version amongst the choices
    :type highest: packaging.version.Version
    :param others: Other known Version detected within (same venv) ``.lock`` files
    :type others: set[packaging.version.Version]
    :returns:

        set_acceptable, lst_specifiers, is_eq_affinity

    :rtype: tuple[set[packaging.specifiers.SpecifierSet], list[list[str]], packaging.version.Version | None]
    """
    dotted_path = f"{g_app_name}.lock_discrepancy.filter_acceptable"

    def acceptable_version(set_ss: set[SpecifierSet], v_test: Version) -> bool:
        """Satisfies all SpecifierSet"""
        ret = all([v_test in ss for ss in set_ss])
        return ret

    # Discard unacceptable versions (from .lock)
    set_highest = set()
    if highest is not None:
        set_highest.add(highest)
    set_all = others.union(set_highest)
    set_acceptable = set()
    for ver in set_all:
        if acceptable_version(set_ss, ver):
            set_acceptable.add(ver)
        else:  # pragma: no cover
            pass

    # By pkg_name, from ``.in`` files
    lsts_specifiers = _get_specifiers(set_pindatum)

    if is_module_debug:  # pragma: no cover
        msg_info = f"{dotted_path} lsts_specifiers (before) {lsts_specifiers!r} "
        _logger.info(msg_info)
    else:  # pragma: no cover
        pass

    # Remove empty list(s)
    empty_idx = []
    for idx, lst_specifiers in enumerate(lsts_specifiers):
        if len(lst_specifiers) == 0:
            empty_idx.append(idx)
        else:  # pragma: no cover
            pass
    #    reversed so higher idx removed first
    for idx in reversed(empty_idx):
        del lsts_specifiers[idx]

    if is_module_debug:  # pragma: no cover
        msg_info = f"{dotted_path} lsts_specifiers (after) {lsts_specifiers!r}"
        _logger.info(msg_info)
    else:  # pragma: no cover
        pass

    # remove from set_acceptable any '!='
    # '==' exclude all other versions
    is_eq_affinity = False
    is_eq_affinity_value = None
    for idx, lst_specifiers in enumerate(lsts_specifiers):
        specifiers = _parse_specifiers(lst_specifiers)
        if is_module_debug:  # pragma: no cover
            msg_info = f"{dotted_path} specifiers {specifiers!r}"
            _logger.info(msg_info)
        else:  # pragma: no cover
            pass
        for t_spec in specifiers:
            oper, ver = t_spec
            ver_version = Version(ver)
            if oper == "!=":
                if is_module_debug:  # pragma: no cover
                    msg_info = f"{dotted_path} {oper!s} {ver_version!r}"
                    _logger.info(msg_info)
                else:  # pragma: no cover
                    pass
                set_acceptable.discard(ver_version)
            elif oper == "==":
                # Discard all except ver
                is_eq_affinity = True
                unlock_ver = ver_version
                is_eq_affinity_value = unlock_ver
                set_remove_these = set()
                for ver_acceptable in set_acceptable:
                    if is_module_debug:  # pragma: no cover
                        msg_info = (
                            f"{dotted_path} ver_acceptable {ver_acceptable!r} "
                            f"ver_version {ver_version!r}"
                        )
                        _logger.info(msg_info)
                    else:  # pragma: no cover
                        pass
                    # Won't be in set_acceptable
                    if ver_acceptable != ver_version:  # pragma: no cover
                        set_remove_these.add(ver_acceptable)
                    else:  # pragma: no cover
                        pass
                # Remove all elements of set B from this set A
                set_acceptable.difference_update(set_remove_these)
                if is_module_debug:  # pragma: no cover
                    msg_info = (
                        f"{dotted_path} {oper!s} {ver_version!r} "
                        f"is_eq_affinity {is_eq_affinity} "
                        f"is_eq_affinity_value {is_eq_affinity_value!r} "
                        f"set_acceptable {set_acceptable!r}"
                    )
                    _logger.info(msg_info)
                else:  # pragma: no cover
                    pass
            else:  # pragma: no cover
                pass

    if is_module_debug:  # pragma: no cover
        msg_info = f"{dotted_path} set_acceptable {set_acceptable!r}"
        _logger.info(msg_info)
    else:  # pragma: no cover
        pass

    t_ret = set_acceptable, lsts_specifiers, is_eq_affinity_value

    return t_ret


def get_compatible_release(
    highest: Version,
    lsts_specifiers: list[list[str]],
):
    """
    .. code-block:: text

       highest    = <Version('25.3')>
       lst_specifiers = ['~=25.0']
       lsts_specifiers = [['<=25.3'], ['~=25.0']]
       set_acceptable = {<Version('25.0')>, <Version('25.3')>}

    For nudge pin lock

    Since ``~=25.0`` is equivalent to ``>= 25.0, == 25.*``
    Any other limiter would be on the upper limit Version

    ``highest`` acceptable Version is correct

    For nudge pin unlock

    In the unlock nudge pin, would be nice to take into account all
    lsts_specifiers. Create a set. Combine all and comma separate

    :param highest: Highest Version amongst the choices
    :type highest: packaging.version.Version
    :param lsts_specifiers: specifiers
    :type lsts_specifiers: list[list[str]]
    :returns: lock and unlock nudge pins and True indicates resolvable
    :rtype: tuple[str, str, bool]
    """
    nudge_pin_lock = nudge_pin_lock_v1(highest)

    set_v_identifiers = set()
    for l_specifiers in lsts_specifiers:
        for specifier in l_specifiers:
            set_v_identifiers.add(specifier)
    l_v_identifiers = list(set_v_identifiers)
    nudge_pin_unlock = ", ".join(l_v_identifiers)

    t_ret_v2 = (nudge_pin_lock, nudge_pin_unlock, True)

    return t_ret_v2


def get_the_fixes(
    set_acceptable,
    lsts_specifiers,
    highest,
    is_eq_affinity_value,
    is_ss_count_zero,
):
    """When a ``.lock`` file is created, it is built from:

    - one ``.in`` file
    - recursively resolved constraints and requirements files

    But not all. Therein lies the rub. Trying to choose based on the
    limited info at hand.

    This algo will fail when there is an unnoticed pin that limits
    the version.

    :py:meth:`~wreck.lock_discrepancy.get_ss_set` has already filtered invalid operators

    :param set_acceptable: Set of acceptable
    :type set_acceptable: set[packaging.specifiers.SpecifierSet]
    :param lsts_specifiers: specifiers
    :type lsts_specifiers: list[list[str]]
    :param highest: Highest Version amongst the choices
    :type highest: packaging.version.Version
    :param is_eq_affinity_value: A Specifier explicitly limits to one version
    :type is_eq_affinity_value: packaging.version.Version | None
    :param is_ss_count_zero: True if set_ss is empty otherwise False
    :type is_ss_count_zero: bool
    :returns:

       lock nudge pin w/o preceding pkg_name
       unlock nudge pin w/o preceding pkg_name
       bool False if unresolvable otherwise True

    :rtype: tuple[str | None, str | None, bool]
    :raises:

       - :py:exc:`wreck.exceptions.PinMoreThanTwoSpecifiers` --
         a pin contains >2 specifiers

       - :py:exc:`wreck.exceptions.ArbitraryEqualityNotImplemented` --
         ``===`` operator not implemented

    """
    dotted_path = f"{g_app_name}.lock_discrepancy.get_the_fixes"

    t_ret = None

    # Test highest
    if is_eq_affinity_value is not None:
        # A specifier explicitly limits to only one version
        unlock_operator = "=="
        nudge_pin_unlock = nudge_pin_unlock_v1(unlock_operator, is_eq_affinity_value)
        nudge_pin_lock = nudge_pin_lock_v1(is_eq_affinity_value)
        t_ret = (nudge_pin_lock, nudge_pin_unlock, True)
    elif is_ss_count_zero:
        # No specifiers limiting versions. Choose highest
        found = highest
        unlock_operator = ">="
        nudge_pin_unlock = nudge_pin_unlock_v1(unlock_operator, found)
        nudge_pin_lock = nudge_pin_lock_v1(found)
        t_ret = (nudge_pin_lock, nudge_pin_unlock, True)
    elif len(set_acceptable) == 0:
        # Unresolvable. No acceptable choices
        t_ret = (None, None, False)
    else:  # pragma: no cover
        pass

    if t_ret is not None:
        return t_ret
    else:
        # Trying to find affinity tuple (operator, ver)
        # Defaults:
        unlock_operator = "=="
        unlock_ver = None

        for idx, lst_specifiers in enumerate(lsts_specifiers):
            if len(lst_specifiers) == 1:
                specifiers = _parse_specifiers(lst_specifiers)
                if is_module_debug:  # pragma: no cover
                    msg_info = (
                        f"{dotted_path} {idx!s} {specifiers!r} {lst_specifiers!r}"
                    )
                    _logger.info(msg_info)
                else:  # pragma: no cover
                    pass
                has_specifiers = len(specifiers) != 0
                if has_specifiers:
                    t_spec = specifiers[0]
                    oper, ver = t_spec

                    if oper in ("!=", "=="):
                        # ``!=`` -- acceptable_version filtered out {ver}
                        # ``==`` -- default unlock operator
                        continue
                    elif oper in ("~="):
                        # compatible release operator ``~=``
                        t_ret_v2 = get_compatible_release(
                            highest,
                            lsts_specifiers,
                        )
                        return t_ret_v2
                    else:
                        # ``>``, ``>=``, ``<``, ``<=``
                        unlock_operator = oper
                        unlock_ver = ver
                        continue
                else:  # pragma: no cover
                    pass
            elif len(lst_specifiers) == 2:
                specifiers = _parse_specifiers(lst_specifiers)
                t_spec_0 = specifiers[0]
                t_spec_1 = specifiers[1]
                oper_0, ver_0 = t_spec_0
                oper_1, ver_1 = t_spec_1

                # compatible release operator ``~=``
                two_opers = (oper_0, oper_1)
                if "~=" in two_opers:
                    # Combine (union) all version identifiers
                    # nudge_pin_lock = nudge_pin_lock_v1(unlock_ver)
                    # nudge_pin_unlock = f"{oper_0}{ver_0!s}, {oper_1}{ver_1!s}"
                    t_ret_v2 = get_compatible_release(
                        highest,
                        lsts_specifiers,
                    )
                    return t_ret_v2
                else:  # pragma: no cover
                    pass

                is_excluded_0 = Version(ver_0) not in set_acceptable
                is_excluded_1 = Version(ver_1) not in set_acceptable
                if is_excluded_0 and is_excluded_1:
                    # Both of these already filtered out, but affects unlock_operator
                    continue
                elif is_excluded_0:
                    if oper_1 in ("=="):
                        # ``==`` -- default unlock operator
                        continue
                    else:
                        unlock_operator = oper_1
                        unlock_ver = ver_1
                elif is_excluded_1:
                    if oper_0 in ("=="):
                        # ``==`` -- default unlock operator
                        continue
                    else:
                        unlock_operator = oper_0
                        unlock_ver = ver_0
                else:
                    """Take 1st specifier [">=24.1", "<25"]. ver 25 most
                    likely doesn't exist
                    """
                    if oper_0 in ("=="):
                        # ``!=`` -- acceptable_version will filtered out
                        # ``==`` -- default unlock operator
                        continue
                    else:
                        unlock_operator = oper_0
                        unlock_ver = ver_0
            else:
                # NotImplementedError --> UnResolvable
                msg_warn = (
                    "A pin containing >2 specifiers is not supported "
                    f"{lsts_specifiers}"
                )
                raise PinMoreThanTwoSpecifiers(msg_warn)

        if unlock_ver is None:
            # Take highest from amongst the acceptable versions
            lst_sorted = sorted(list(set_acceptable))
            found = lst_sorted[-1]
            # unlock_operator = "=="
            # t_ret = (set_ss, unlock_operator, found)
            nudge_pin_lock = nudge_pin_lock_v1(found)
            t_ret_v2 = (nudge_pin_lock, nudge_pin_lock, True)
            return t_ret_v2
        else:  # pragma: no cover
            pass

        if is_module_debug:  # pragma: no cover
            msg_info = (
                f"{dotted_path} (before operator func chooser) "
                f"unlock operator {unlock_operator} "
                f"unlock_ver {unlock_ver} highest {highest}"
            )
            _logger.info(msg_info)
        else:  # pragma: no cover
            pass

        specifier_len = _specifier_length(unlock_operator)
        is_arbitrary_equality = specifier_len == 3 and unlock_operator == "==="
        if is_arbitrary_equality:
            # ArbitraryEqualityNotImplemented --> UnResolvable
            msg_info = f"{dotted_path} operator not implemented {unlock_operator}"
            raise ArbitraryEqualityNotImplemented(msg_info)
        elif specifier_len == 2 and unlock_operator == "==":
            # unlock_ver is Non-None
            func = None
            idx_from_list = None
            found = unlock_ver
        elif (specifier_len == 2 and unlock_operator in "<=") or (
            specifier_len == 1 and unlock_operator in "<"
        ):
            # le or lt
            found = highest
            nudge_pin_lock = nudge_pin_lock_v1(found)
            nudge_pin_unlock = nudge_pin_unlock_v1(unlock_operator, unlock_ver)
            t_ret_v2 = (nudge_pin_lock, nudge_pin_unlock, True)
            return t_ret_v2
        elif specifier_len == 2 and unlock_operator in ">=":
            # version ge and closest to unlock_ver
            # remove versions < unlock_ver. Then take highest
            func = operator.ge
            idx_from_list = -1
        elif specifier_len == 1 and unlock_operator in ">":
            # version gt unlock_ver and closest to unlock_ver
            # remove versions <= unlock_ver. Then take highest
            func = operator.gt
            idx_from_list = -1
        else:  # pragma: no cover
            # Invalid operators already filtered out by call to get_ss_set
            pass

        if func is not None:
            lst = [
                ver_test
                for ver_test in set_acceptable
                if func(ver_test, Version(unlock_ver))
            ]
            if len(lst) != 0:
                lst_sorted = sorted(lst)
                found = lst_sorted[idx_from_list]
                nudge_pin_unlock = nudge_pin_unlock_v1(unlock_operator, found)
                nudge_pin_lock = nudge_pin_lock_v1(found)
                t_ret_v2 = (nudge_pin_lock, nudge_pin_unlock, True)
            else:
                # Unresolvable
                t_ret_v2 = (None, None, False)
        else:
            # ==
            nudge_pin_lock = nudge_pin_lock_v1(found)
            t_ret_v2 = (nudge_pin_lock, nudge_pin_lock, True)

    return t_ret_v2


@dataclass(**DC_SLOTS)
class Resolvable:
    """Resolvable dependency conflict. Can find the lines for the pkg,
    in ``.unlock`` and ``.lock`` files, using (loader and)
    venv_path and pkg_name.

    Limitation: Qualifiers
    e.g. python_version and os_name

    - haphazard usage

    All pkg lines need the same qualifier. Often missing. Make uniform.
    Like a pair of earings.

    - rigorous usage

    There can be one or more qualifiers. In which case, nonobvious which qualifier
    to use where.

    :ivar venv_path: Relative or absolute path to venv base folder
    :vartype venv_path: str | pathlib.Path
    :ivar pkg_name: package name
    :vartype pkg_name: str
    :ivar qualifiers:

       qualifiers joined together into one str. Whitespace before the
       1st semicolon not preserved.

    :vartype qualifiers: str
    :ivar nudge_unlock:

       For ``.unlock`` files. Nudge pin e.g. ``pkg_name>=some_version``.
       If pkg_name entry in an ``.unlock`` file, replace otherwise add entry

    :vartype nudge_unlock: str
    :ivar nudge_lock:

       For ``.lock`` files. Nudge pin e.g. ``pkg_name==some_version``.
       If pkg_name entry in a ``.lock`` file, replace otherwise add entry

    :vartype nudge_lock: str
    """

    venv_path: str | Path
    pkg_name: str
    qualifiers: str
    nudge_unlock: str
    nudge_lock: str


@dataclass(**DC_SLOTS)
class UnResolvable:
    """Cannot resolve this dependency conflict.

    Go out of our way to clearly and cleanly present sufficient
    details on the issue.

    The most prominent details being the package name and Pins
    (from relevant ``.unlock`` files).

    **Track down issue**

    With issue explanation. Look at the ``.lock`` to see the affected
    package's parent(s). The parents' package pins may be the cause of
    the conflict.

    The parents' package ``pyproject.toml`` file is the first place to look
    for strange dependency restrictions. Why a restriction was imposed upon a
    dependency may not be well documented. Look in the repo issues. Search for
    the dependency package name

    **Upgrading**

    lock inspect is not a dependency upgrader. Priority is to sync
    ``.unlock`` and ``.lock`` files.

    Recommend always doing a dry run
    :code:`pip compile --dry-run some-requirement.in` or
    looking at upgradable packages within the venv. :code:`pip list -o`

    :ivar venv_path: Relative or absolute path to venv base folder
    :vartype venv_path: str | pathlib.Path
    :ivar pkg_name: package name
    :vartype pkg_name: str
    :ivar qualifiers:

       qualifiers joined together into one str. Whitespace before the
       1st semicolon not preserved.

    :vartype qualifiers: str
    :ivar sss:

       Set of SpecifierSet, for this package, are the dependency version
       restrictions found in ``.unlock`` files

    :vartype sss: set[packaging.specifiers.SpecifierSet]
    :ivar v_highest:

       Hints at the process taken to find a Version which
       satisfies SpecifierSets. First this highest version was checked

    :vartype v_highest: packaging.version.Version
    :ivar v_others:

       After highest version, all other potential versions are checked.
       The potential versions come from the ``.lock`` files. So if a
       version doesn't exist in one ``.lock``, it's never tried.

    :vartype v_others: set[packaging.version.Version]
    :ivar pins:

       Has the absolute path to each requirements file and the dependency
       version restriction.

       Make this readable

    :vartype pins: set[wreck.lock_datum.PinDatum]
    """

    venv_path: str
    pkg_name: str
    qualifiers: str
    sss: set[SpecifierSet]
    v_highest: Version
    v_others: set[Version]
    pins: set[PinDatum]

    def __repr__(self):
        """Emphasis is on presentation, not reproducing an instance.

        :returns: Readable presentation of the unresolvable dependency conflict
        :rtype: str
        """
        cls_name = self.__class__.__name__
        ret = (
            f"<{cls_name} pkg_name='{self.pkg_name}' venv_path='{self.venv_path!s}' \n"
        )
        ret += f"qualifiers='{self.qualifiers}' sss={self.sss!r} \n"
        ret += f"v_highest={self.v_highest!r} v_others={self.v_others!r} \n"
        ret += f"pins={pprint_pins(self.pins)}>"

        return ret


@dataclass(**DC_SLOTS)
class ResolvedMsg:
    """Fixed dependency version discrepancies (aka issues)

    Does not include the original line

    :ivar venv_path: venv relative or absolute path
    :vartype venv_path: str
    :ivar abspath_f: Absolute path to requirements file
    :vartype abspath_f: pathlib.Path
    :ivar nudge_pin_line: What the line will become
    :vartype nudge_pin_line: str
    """

    venv_path: str
    abspath_f: Path
    nudge_pin_line: str


def extract_full_package_name(line, pkg_name_desired):
    """Extract first occurrence of exact package name. Algo uses tokens, not regex.

    :param line:

       .unlock or .lock file line. Has package name, but might not be exact

    :type line: str
    :param pkg_name_desired: pkg name would like an exact match
    :type pkg_name_desired: str
    :returns:

       is_different_pkg -- True indicates can be either similar or different package
       is_known_oper -- None means could not parse line. bool known/unknown operator
       pkg -- package name. Alphanumeric hyphen underscore and period
       oper - operator e.g. ``>=``
       remaining -- everything following the operator

    :rtype: tuple[bool, bool | None, str | None, str | None, str | None]

    .. seealso::

       `pep044 <https://peps.python.org/pep-0440>`_
       `escape characters <https://docs.python.org/3/library/re.html#re.escape>`_

    """
    t_tokens = (";", "@", "===", "==", "<=", ">=", "<", ">", "~=", "!=")
    smallest_idx = None
    smallest_token = None
    for token in t_tokens:
        is_in = token in line
        if is_in:
            idx_current = line.index(token)
            if smallest_idx is None:
                smallest_token = token
                smallest_idx = idx_current
            else:
                if idx_current < smallest_idx:
                    smallest_token = token
                    smallest_idx = idx_current
                else:  # pragma: no cover
                    pass
        else:  # pragma: no cover
            pass

    if smallest_idx is not None:
        # up to 1st known token
        pkg = line[:smallest_idx]
        pkg = pkg.strip()
        oper = smallest_token
        remaining = line[line.index(smallest_token) + len(smallest_token) :]
        remaining = remaining.strip()
        is_known_oper = True
    else:
        # no token case
        # pattern_pkg_only = r"^([-\w]+)\s?\b"
        """

        .. code-block:: text

           pattern_pkg_only = r'^(.*)'
           m_pkg_only = re.match(pattern_pkg_only, line)

           if m_pkg_only is not None:
               groups_pkg_only = m_pkg_only.groups()
           else:
               groups_pkg_only = None

        """

        pass

        """unknown token case

        There are three groups.

        - one or more hyphen | word characters,
        - maybe a space,
        - 1-3 non-decimal characters,
        - maybe a space,
        - everything else

        pip-requirements-parser ~~ 24.2
        pip-requirements-parser~~24.2
        """
        pattern = r"^([-\w]+)\s?(\D{1,3})?\s?(.*)?"
        m = re.match(pattern, line)

        if m is not None:
            groups = m.groups()
            # If just a pkg name :code:`groups == ('tomli', None, '')`
            pkg = groups[0]
            oper = groups[1]
            if oper is None:
                # pkg name only
                pkg = pkg.strip()
                oper = ""
                remaining = ""
                is_known_oper = True
            else:
                # unsupported/unexpected token
                pkg = pkg.strip()
                oper = groups[1]
                oper = oper.strip()
                remaining = groups[2]
                remaining = remaining.strip()
                is_known_oper = False
        else:
            # planned but not yet supported pattern e.g. remote URL
            pkg = None
            oper = None
            remaining = None
            is_known_oper = None

    # Confirm expected term, not more
    # tox-gh-actions not tox
    is_different_pkg = pkg is not None and pkg != pkg_name_desired

    ret = (is_different_pkg, is_known_oper, pkg, oper, remaining)

    return ret


def write_to_file_nudge_pin(path_f, pkg_name, nudge_pin_line):
    """Nudge pin must include a newline (os.linesep)
    If package line exists in file, overwrite. Otherwise append nudge pin line

    :param path_f:

       Absolute path to either a ``.unlock`` or ``.lock`` file. Only a
       comment if no preceding whitespace

    :type path_f: pathlib.Path
    :param pkg_name: Package name. Should be lowercase
    :type pkg_name: str
    :param nudge_pin_line:

       Format ``[package name][operator][version][qualifiers][os.linesep]``

    :type nudge_pin_line: str
    """
    with io.StringIO() as g:
        # Do not assume the .unlock file already exists
        if not path_f.exists():
            path_f.touch()
        else:  # pragma: no cover
            pass

        with open(path_f, mode="r", encoding="utf-8") as f:
            is_found = False
            for line in f:
                is_empty_line = len(line.strip()) == 0
                is_comment = line.startswith("#")

                # Need an exact match
                t_actual = extract_full_package_name(line, pkg_name)
                is_different_pkg, is_known_oper, pkg, oper, remaining = t_actual
                #    both ok
                # is_no_oper = is_known_oper and oper is not None and len(oper) == 0
                #    also is_known_oper is None
                is_line_issue = pkg is None
                if (
                    is_empty_line
                    or is_comment
                    or is_line_issue
                    or is_different_pkg
                    or (is_known_oper is not None and is_known_oper is False)
                ):
                    g.writelines([line])
                else:
                    # found. Replace line rather than remove line
                    is_found = True
                    g.writelines([nudge_pin_line])

        # covers cases: for-else the file is empty, no such package line found
        if not is_found:
            # not replaced, append line
            g.writelines([nudge_pin_line])
        else:  # pragma: no cover
            pass
        contents = g.getvalue()

    # overwrites entire file
    path_f.write_text(contents)
