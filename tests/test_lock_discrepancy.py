"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Unit test -- Module

.. code-block:: shell

   python -m coverage run --source='wreck.lock_discrepancy' -m pytest \
   --showlocals tests/test_lock_discrepancy.py && coverage report \
   --data-file=.coverage --include="**/lock_discrepancy.py"

"""

from contextlib import nullcontext as does_not_raise
from pathlib import Path

import pytest
from logging_strict.tech_niques import get_locals_dynamic  # noqa: F401
from packaging.specifiers import InvalidSpecifier
from packaging.version import Version

from wreck._safe_path import resolve_joinpath
from wreck.constants import g_app_name
from wreck.exceptions import (
    ArbitraryEqualityNotImplemented,
    PinMoreThanTwoSpecifiers,
)
from wreck.lock_datum import PinDatum
from wreck.lock_discrepancy import (
    UnResolvable,
    _parse_specifiers,
    _specifier_length,
    extract_full_package_name,
    filter_acceptable,
    get_ss_set,
    get_the_fixes,
)

testdata_extract_full_package_name = (
    (
        'colorama ;platform_system=="Windows"',
        "colorama",
        "colorama",
        False,
    ),
    (
        'tomli; python_version<"3.11"',
        "tomli",
        "tomli",
        False,
    ),
    (
        "pip @ remote",
        "pip",
        "pip",
        False,
    ),
    (
        "pip@ remote",
        "pip",
        "pip",
        False,
    ),
    (
        "pip @remote",
        "pip",
        "pip",
        False,
    ),
    (
        "tox>=1.1.0",
        "tox",
        "tox",
        False,
    ),
    (
        "tox-gh-action>=1.1.0",
        "tox",
        "tox-gh-action",
        False,
    ),
    (
        'tomli>=2.2.1; python_version<"3.11"',
        "tomli",
        "tomli",
        False,
    ),
    (
        'tomli>=2.2.1; python_version<"3.11" ;platform_system=="Windows"',
        "tomli",
        "tomli",
        False,
    ),
    (
        'tomli ; python_version<"3.11" ;platform_system=="Windows"',
        "tomli",
        "tomli",
        False,
    ),
    (
        "tomli",
        "pip",
        "tomli",
        False,
    ),
    (
        "pip-requirements-parser ~~ 24.2",
        "pip-requirements-parser",
        "pip-requirements-parser",
        True,
    ),
    (
        "pip-requirements-parser~~24.2",
        "pip-requirements-parser",
        "pip-requirements-parser",
        True,
    ),
    (
        "namespaces.py <= 1.0.1",
        "namespaces.py",
        "namespaces.py",
        False,
    ),
)
ids_extract_full_package_name = (
    "space semicolon",
    "semicolon space",
    "space at space",
    "at space",
    "space at",
    "exact pkg name operator ge",
    "not a match",
    "pkg with specifier and qualifier",
    "pkg with specifier and two qualifiers",
    "pkg without specifier and two qualifiers",
    "unrelated package",
    "pkg name with hyphens or underscores and unknown token possible whitespace",
    "pkg name with hyphens or underscores and unknown token no whitespace",
    "pkg name containing a period",
)


@pytest.mark.logging_package_name(g_app_name)
@pytest.mark.parametrize(
    "line, search_for, expected_pkg_name, is_needs_fix",
    testdata_extract_full_package_name,
    ids=ids_extract_full_package_name,
)
def test_extract_full_package_name(
    line,
    search_for,
    expected_pkg_name,
    is_needs_fix,
    logging_strict,
):
    """For a particular package, check line is an exact match."""
    # pytest -vv --showlocals --log-level INFO -k "test_extract_full_package_name" tests
    # pytest -vv --showlocals --log-level INFO tests/test_lock_discrepancy.py::test_extract_full_package_name[unrelated\ package]
    t_two = logging_strict()
    logger, loggers = t_two

    """
    args = (line, search_for)
    kwargs = {}
    t_ret = get_locals_dynamic(  # noqa: F841
        extract_full_package_name,
        *args,
        **kwargs,
    )
    """

    t_match = extract_full_package_name(line, search_for)
    is_different_pkg, is_known_oper, pkg_name_actual, oper, remaining = t_match

    if pkg_name_actual is None:
        # not supported yet
        assert pkg_name_actual == expected_pkg_name
    else:
        is_no_oper = is_known_oper and oper is not None and len(oper) == 0
        if is_no_oper and is_different_pkg:
            # tox and mypy (not pin)
            assert pkg_name_actual == expected_pkg_name
        elif is_no_oper and not is_different_pkg:
            # tox and tox (not pin)
            assert pkg_name_actual == expected_pkg_name
        else:
            if is_different_pkg and is_known_oper:
                # mypy vs tox, tox-gh-action vs tox
                assert pkg_name_actual == expected_pkg_name
            elif not is_different_pkg and is_known_oper:
                # same and known operator e.g. tox vs tox
                assert pkg_name_actual == expected_pkg_name
            else:
                # unknown operator in different or same pkg. This is a fix issue
                assert is_needs_fix is True

    # Couldn't figure out how to make re.match fail
    """
    with patch("re.match", return_value=None):
        pkg_name_actual = extract_full_package_name(line, "%%")
        assert pkg_name_actual is None
    """
    pass


testdata_choose_version_order_mixed_up = (
    (
        "pip",
        (
            "file_0.in",
            '"pip>=24.2; python_version <= "3.10"',
            [">=24.2"],
            ['python_version <= "3.10"'],
        ),
        (
            "file_1.in",
            "pip",
            [],
            [],
        ),
        Version("23.0"),
        {Version("25.0"), Version("24.8"), Version("25.3")},
        does_not_raise(),
        ">=",
        Version("25.3"),
        True,
    ),
    (
        "pip",
        (
            "file_0.in",
            '"pip; python_version <= "3.10"',
            [],
            ['python_version <= "3.10"'],
        ),
        (
            "file_1.in",
            "pip",
            [],
            [],
        ),
        Version("25.3"),
        {Version("25.0"), Version("23.0"), Version("24.8")},
        does_not_raise(),
        ">=",
        Version("25.3"),
        True,
    ),
    (
        "pip",
        (
            "file_0.in",
            '"pip != 25.3; python_version <= "3.10"',
            ["!=25.3"],
            ['python_version <= "3.10"'],
        ),
        (
            "file_1.in",
            "pip",
            [],
            [],
        ),
        Version("25.3"),
        {Version("25.0"), Version("23.0"), Version("24.8")},
        does_not_raise(),
        "==",
        Version("25.0"),
        True,
    ),
    (
        "pip",
        (
            "file_0.in",
            '"pip; python_version <= "3.10"',
            [],
            ['python_version <= "3.10"'],
        ),
        (
            "file_1.in",
            "pip",
            [],
            [],
        ),
        Version("25.3"),
        {Version("25.0"), Version("23.0"), Version("24.8")},
        does_not_raise(),
        ">=",
        Version("25.3"),
        True,
    ),
    (
        "pip",
        (
            "file_0.in",
            '"pip==25.0; python_version <= "3.10"',
            ["==25.0"],
            ['python_version <= "3.10"'],
        ),
        (
            "file_1.in",
            "pip<=25.3",
            ["<=25.3"],
            [],
        ),
        Version("25.3"),
        {Version("25.0"), Version("23.0"), Version("24.8")},
        does_not_raise(),
        "==",
        Version("25.0"),
        True,
    ),
    (
        "pip",
        (
            "file_0.in",
            '"pip~=25.0; python_version <= "3.10"',
            ["~=25.0"],
            ['python_version <= "3.10"'],
        ),
        (
            "file_1.in",
            "pip<=25.3",
            ["<=25.3"],
            [],
        ),
        Version("25.3"),
        {Version("25.0"), Version("23.0"), Version("24.8")},
        does_not_raise(),
        "~=",
        Version("25.3"),
        True,
    ),
    (
        "pip",
        (
            "file_0.in",
            '"pip>=23.0, <25.3; python_version <= "3.10"',
            [">=23.0", "<25.3"],
            ['python_version <= "3.10"'],
        ),
        (
            "file_1.in",
            "pip",
            [],
            [],
        ),
        Version("25.3"),
        {Version("25.0"), Version("23.0"), Version("24.8")},
        does_not_raise(),
        ">=",
        Version("25.0"),
        True,
    ),
    (
        "pip",
        (
            "file_0.in",
            '"pip>=23.0, <25.3, !=25.2; python_version <= "3.10"',
            [">=23.0", "<25.3", "!=25.2"],
            ['python_version <= "3.10"'],
        ),
        (
            "file_1.in",
            "pip",
            [],
            [],
        ),
        Version("25.3"),
        {Version("25.0"), Version("23.0"), Version("24.8")},
        pytest.raises(PinMoreThanTwoSpecifiers),
        ">=",
        Version("25.0"),
        False,
    ),
    (
        "pip",
        (
            "file_0.in",
            '"pip~=23.0, <=23.3; python_version <= "3.10"',
            ["~=23.0", "<=23.3"],
            ['python_version <= "3.10"'],
        ),
        (
            "file_1.in",
            "pip!=23.4",
            ["!=23.4"],
            [],
        ),
        Version("23.3"),
        {Version("23.0"), Version("23.1"), Version("23.3")},
        does_not_raise(),
        "~=23.0, <=23.3, !=23.4",
        Version("23.3"),
        True,
    ),
    (
        "pip",
        (
            "file_1.in",
            "pip!=23.4",
            ["!=23.4"],
            [],
        ),
        (
            "file_0.in",
            '"pip~=23.0, <=23.3; python_version <= "3.10"',
            ["~=23.0", "<=23.3"],
            ['python_version <= "3.10"'],
        ),
        Version("23.3"),
        {Version("23.0"), Version("23.1"), Version("23.3")},
        does_not_raise(),
        "~=23.0, <=23.3, !=23.4",
        Version("23.3"),
        True,
    ),
    (
        "pip",
        (
            "file_0.in",
            '"pip>=23.0, !=22.3; python_version <= "3.10"',
            [">=23.0", "!=22.3"],
            ['python_version <= "3.10"'],
        ),
        (
            "file_1.in",
            "pip",
            [],
            [],
        ),
        Version("25.3"),
        {Version("25.0"), Version("23.0"), Version("24.8")},
        does_not_raise(),
        ">=",
        Version("25.3"),
        True,
    ),
    (
        "pip",
        (
            "file_0.in",
            '"pip<24.2; python_version <= "3.10"',
            ["<24.2"],
            ['python_version <= "3.10"'],
        ),
        (
            "file_1.in",
            "pip",
            [],
            [],
        ),
        Version("24.1"),
        {Version("23.0"), Version("23.5"), Version("24.0")},
        does_not_raise(),
        "<24.2",
        Version("24.1"),
        True,
    ),
    (
        "pip",
        (
            "file_0.in",
            '"pip>24.2; python_version <= "3.10"',
            [">24.2"],
            ['python_version <= "3.10"'],
        ),
        (
            "file_1.in",
            "pip",
            [],
            [],
        ),
        Version("25.3"),
        {Version("24.3"), Version("24.5"), Version("25.0")},
        does_not_raise(),
        ">24.2",
        Version("25.3"),
        True,
    ),
    (
        "pip",
        (
            "file_0.in",
            '"pip~~24.2; python_version <= "3.10"',
            ["~~24.2"],
            ['python_version <= "3.10"'],
        ),
        (
            "file_1.in",
            "pip",
            [],
            [],
        ),
        Version("25.3"),
        {Version("24.3"), Version("24.5"), Version("25.0")},
        pytest.raises(InvalidSpecifier),
        "~~24.2",
        Version("25.3"),
        True,
    ),
    (
        "pip",
        (
            "file_0.in",
            '"pip==24.2; python_version <= "3.10"',
            ["==24.2"],
            ['python_version <= "3.10"'],
        ),
        (
            "file_1.in",
            "pip",
            [],
            [],
        ),
        Version("24.2"),
        set(),
        does_not_raise(),
        "==24.2",
        Version("24.2"),
        True,
    ),
    (
        "pip",
        (
            "file_0.in",
            '"pip===24.2; python_version <= "3.10"',
            ["===24.2"],
            ['python_version <= "3.10"'],
        ),
        (
            "file_1.in",
            "pip",
            [],
            [],
        ),
        Version("24.2"),
        set(),
        pytest.raises(ArbitraryEqualityNotImplemented),
        "===24.2",
        Version("24.2"),
        False,
    ),
    (
        "pip",
        (
            "file_0.in",
            '"pip<=23.0; python_version <= "3.10"',
            ["<=23.0"],
            ['python_version <= "3.10"'],
        ),
        (
            "file_1.in",
            "pip",
            [],
            [],
        ),
        Version("22.8"),
        {Version("22.0"), Version("22.1"), Version("22.6")},
        does_not_raise(),
        "<=",
        Version("22.8"),
        True,
    ),
    (
        "pip",
        (
            "file_0.in",
            '"pip<=23.0; python_version <= "3.10"',
            ["<=23.0"],
            ['python_version <= "3.10"'],
        ),
        (
            "file_1.in",
            "pip",
            [],
            [],
        ),
        None,
        set(),
        does_not_raise(),
        None,
        None,
        False,
    ),
    (
        "pip",
        (
            "file_0.in",
            "pip<24.2",
            ["<24.2"],
            [],
        ),
        (
            "file_1.in",
            "pip>=24.2",
            [">=24.2"],
            [],
        ),
        None,
        set(),
        does_not_raise(),
        None,
        None,
        False,
    ),
)
ids_choose_version_order_mixed_up = (
    ">=24.2 out of order others set",
    "No specifiers provided. Version chosen solely from version in .lock files",
    "!=25.3 --> next best choice ==25.0",
    "package twice without specifiers",
    "==25.0 all other package version become unacceptable",
    "~= not yet supported",
    "two specifiers",
    "three specifiers",
    "compatible_release two version identifiers",
    "compatible_release two version identifiers pins order reversed",
    "already excluded by other version identifier",
    "lt operator",
    "gt operator",
    "unsupported operator ~~",
    "== operator",
    "=== operator not implemented",
    "le operator",
    "unresolvable 1",
    "unresolvable 2",
)


@pytest.mark.logging_package_name(g_app_name)
@pytest.mark.parametrize(
    (
        "pkg_name, seq_file_0, seq_file_1, highest, others, expectation, "
        "unlock_operator_expected, found_expected, is_found_expected"
    ),
    testdata_choose_version_order_mixed_up,
    ids=ids_choose_version_order_mixed_up,
)
def test_choose_version_order_mixed_up(
    pkg_name,
    seq_file_0,
    seq_file_1,
    highest,
    others,
    expectation,
    unlock_operator_expected,
    found_expected,
    is_found_expected,
    tmp_path,
    logging_strict,
):
    """Have versions in others out of order."""
    # pytest -vv --showlocals --log-level INFO -k "test_choose_version_order_mixed_up" tests
    t_two = logging_strict()
    logger, loggers = t_two

    f_relpath_0, line_0, specifiers_0, qualifiers_0 = seq_file_0
    f_relpath_1, line_1, specifiers_1, qualifiers_1 = seq_file_1
    file_abspath_0 = resolve_joinpath(tmp_path, f_relpath_0)
    file_abspath_1 = resolve_joinpath(tmp_path, f_relpath_1)

    pind_0 = PinDatum(
        file_abspath_0,
        pkg_name,
        line_0,
        specifiers_0,
        qualifiers_0,
    )
    pind_1 = PinDatum(
        file_abspath_1,
        pkg_name,
        line_1,
        specifiers_1,
        qualifiers_1,
    )
    set_pindatum = set()
    set_pindatum.add(pind_0)
    set_pindatum.add(pind_1)

    """
    args = (set_pindatum, highest, others)
    kwargs = {}
    t_out = get_locals_dynamic(  # noqa: F841
        get_the_fixes,
        *args,
        **kwargs,
    )
    t_ret, t_locals = t_out
    """
    with expectation:
        # DRY. Needed when UnResolvable
        set_ss = get_ss_set(set_pindatum)
        is_ss_count_zero = len(set_ss) == 0

        t_acceptable = filter_acceptable(
            set_pindatum,
            set_ss,
            highest,
            others,
        )
        set_acceptable, lsts_specifiers, is_eq_affinity_value = t_acceptable
        t_ret = get_the_fixes(
            set_acceptable,
            lsts_specifiers,
            highest,
            is_eq_affinity_value,
            is_ss_count_zero,
        )
    if isinstance(expectation, does_not_raise):
        assert isinstance(t_ret, tuple)
        assert len(t_ret) == 3
        lock_nudge_pin, unlock_nudge_pin, is_found_actual = t_ret
        assert isinstance(is_found_actual, bool)
        assert is_found_actual == is_found_expected

        if is_found_actual is True:
            assert lock_nudge_pin == f"=={found_expected!s}"


testdata_parse_specifiers = (
    (
        [">=24.2"],
        [(">=", "24.2")],
    ),
    (
        ["<=24.2"],
        [("<=", "24.2")],
    ),
    (
        ["<24.2"],
        [("<", "24.2")],
    ),
    (
        [">24.2"],
        [(">", "24.2")],
    ),
    (
        ["!=24.2"],
        [("!=", "24.2")],
    ),
    (
        ["==24.2"],
        [("==", "24.2")],
    ),
    (
        ["~=24.2"],
        [("~=", "24.2")],
    ),
)
ids_parse_specifiers = (
    "ge 24.2",
    "le 24.2",
    "lt 24.2",
    "gt 24.2",
    "ne 24.2",
    "eq 24.2",
    "shortcut for between version and next major release",
)


@pytest.mark.parametrize(
    "specifiers, lst_expected",
    testdata_parse_specifiers,
    ids=ids_parse_specifiers,
)
def test_parse_specifiers(
    specifiers,
    lst_expected,
):
    """Just parse each specifier from str to tuple"""
    # pytest -vv --showlocals --log-level INFO -k "test_parse_specifiers" tests
    # Specifiers produced by pip_requirements_parser.RequirementsFile
    """
    args = (specifiers,)
    kwargs = {}
    t_out = get_locals_dynamic(  # noqa: F841
        _parse_specifiers,
        *args,
        **kwargs,
    )
    lst, t_locals = t_out
    """
    lst = _parse_specifiers(specifiers)

    for idx, t_datum in enumerate(lst):
        assert lst_expected[idx] == t_datum


testdata_specifier_length = (
    (
        "<",
        does_not_raise(),
        1,
    ),
    (
        ">",
        does_not_raise(),
        1,
    ),
    (
        "<=",
        does_not_raise(),
        2,
    ),
    (
        ">=",
        does_not_raise(),
        2,
    ),
    (
        "~=",
        does_not_raise(),
        2,
    ),
    (
        "!=",
        does_not_raise(),
        2,
    ),
    (
        "==",
        does_not_raise(),
        2,
    ),
    (
        "===",
        does_not_raise(),
        3,
    ),
    (
        "!==",
        pytest.raises(ValueError),
        3,
    ),
)
ids_specifier_length = (
    "lt 1",
    "gt 1",
    "le 2",
    "ge 2",
    "compatible release 2",
    "ne 2",
    "eq 2",
    "=== 3",
    "!== ValueError",
)


@pytest.mark.parametrize(
    "specifier, expectation, expected_len",
    testdata_specifier_length,
    ids=ids_specifier_length,
)
def test_specifier_length(specifier, expectation, expected_len):
    """Test operator detection algo."""
    # pytest -vv --showlocals --log-level INFO -k "test_specifier_length" tests
    with expectation:
        actual_len = _specifier_length(specifier)
    if isinstance(expectation, does_not_raise):
        assert actual_len == expected_len


def test_class_unresolvable():
    """repr of UnResolvable"""
    # pytest -vv --showlocals --log-level INFO -k "test_class_unresolvable" tests
    abspath_f = Path(__file__).parent.joinpath(
        "_qualifier_conflicts",
        "qualifier_1.unlock",
    )
    pin_pip_0 = PinDatum(
        abspath_f,
        "pip",
        '"pip>=24.2',
        [">=24.2"],
        [],
    )
    set_pindatum = set()
    set_pindatum.add(pin_pip_0)
    set_ss = get_ss_set(set_pindatum)
    unres = UnResolvable(
        ".venv",
        "pip",
        "",
        set_ss,
        Version("24.5"),
        {Version("24.2"), Version("24.3")},
        set_pindatum,
    )
    str_unres = repr(unres)
    assert str_unres is not None
    assert isinstance(str_unres, str)
