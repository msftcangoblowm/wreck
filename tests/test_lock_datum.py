"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Unit test -- Module

.. code-block:: shell

   python -m coverage run --source='wreck.lock_datum' -m pytest \
   --showlocals tests/test_lock_datum.py && coverage report \
   --data-file=.coverage --include="**/lock_datum.py"

"""

from __future__ import annotations

import shutil
from contextlib import nullcontext as does_not_raise
from pathlib import Path
from typing import cast

import pytest

from wreck._safe_path import resolve_joinpath
from wreck.constants import (
    SUFFIX_LOCKED,
    SUFFIX_UNLOCKED,
)
from wreck.exceptions import MissingPackageBaseFolder
from wreck.lock_collections import Ins
from wreck.lock_datum import (
    InFileType,
    OutLastSuffix,
    PinDatum,
    _hash_pindatum,
    has_qualifiers,
    in_generic,
    is_pin,
    pprint_pins,
)
from wreck.lock_filepins import FilePins
from wreck.pep518_venvs import VenvMapLoader

testdata_pin_methods = (
    (
        Path(__file__).parent.joinpath(
            "_qualifier_conflicts",
            "qualifier_1.unlock",
        ),
        "requirements/qualifier_1.in",
        "pip",
        0,
        True,
    ),
    (
        Path(__file__).parent.joinpath(
            "_qualifier_conflicts",
            "qualifier_1.unlock",
        ),
        "requirements/qualifier_1.in",
        "tomli",
        1,
        True,
    ),
    (
        Path(__file__).parent.joinpath(
            "_qualifier_conflicts",
            "qualifier_1.unlock",
        ),
        "requirements/qualifier_1.in",
        "isort",
        0,
        False,
    ),
    (
        Path(__file__).parent.joinpath(
            "_qualifier_conflicts",
            "qualifier_0.unlock",
        ),
        "requirements/qualifier_0.in",
        "colorama",
        1,
        False,
    ),
)
ids_pin_methods = (
    "various constraints pip",
    "various constraints tomli",
    "various constraints isort",
    "constraints conflicts normalize qualifier",
)


@pytest.mark.parametrize(
    (
        "abspath_req_src, dest_relpath, pkg_name, "
        "qualifiers_expected_count, has_specifiers"
    ),
    testdata_pin_methods,
    ids=ids_pin_methods,
)
def test_pindatum_type(
    abspath_req_src,
    dest_relpath,
    pkg_name,
    qualifiers_expected_count,
    has_specifiers,
    tmp_path,
    prepare_folders_files,
    path_project_base,
):
    """Test PinDatum"""
    # pytest --showlocals --log-level INFO -k "test_pindatum_type" tests
    path_cwd = path_project_base()
    # prepare
    #    empty folders
    seqs_reqs = ("requirements/.python-version",)
    prepare_folders_files(seqs_reqs, tmp_path)

    #    copy a .in file
    src_abspath = str(abspath_req_src)
    abspath_dest = cast("Path", resolve_joinpath(tmp_path, dest_relpath))
    shutil.copy(src_abspath, abspath_dest)

    fp = FilePins(abspath_dest)
    lst_pins_pip = fp.by_pkg(pkg_name)
    assert len(lst_pins_pip) == 1
    pin_pip = lst_pins_pip[0]
    assert isinstance(pin_pip, PinDatum)

    # PinDatum.__hash__
    assert hash(pin_pip) == _hash_pindatum(abspath_dest, pkg_name, pin_pip.qualifiers)
    # __eq__
    assert pin_pip != 7

    # PinDatum.__lt__
    lst = fp._pins
    assert isinstance(sorted(lst), list)

    with pytest.raises(TypeError):
        lst.insert(0, 1.2)
        lst.append(7)
        sorted(lst)

    # PinDatum from different files
    abspath_file_left = cast(
        "Path",
        resolve_joinpath(
            path_cwd,
            "tests/_qualifier_conflicts/qualifier_1.unlock",
        ),
    )
    left_pkg_name = "tomli"
    abspath_file_right = cast(
        "Path",
        resolve_joinpath(
            path_cwd,
            "tests/_qualifier_conflicts/qualifier_0.unlock",
        ),
    )
    right_pkg_name = "colorama"
    with pytest.raises(TypeError):
        fp_left = FilePins(abspath_file_left)
        fp_right = FilePins(abspath_file_right)
        assert isinstance(fp_left, FilePins)
        assert isinstance(fp_right, FilePins)
        PinDatum_left = fp_left.by_pkg(left_pkg_name)[0]
        PinDatum_right = fp_right.by_pkg(right_pkg_name)[0]
        assert isinstance(PinDatum_left, PinDatum)
        assert isinstance(PinDatum_right, PinDatum)

        PinDatum_left < PinDatum_right

    # For purposes of sorting -- pkg_name same, qualifiers same
    pin_left = PinDatum(
        abspath_file_left,
        "colorama",
        'colorama;os_name == "nt"',
        [],
        ['platform_system=="Windows"'],
    )
    pin_right_0 = PinDatum(
        abspath_file_left,
        "colorama",
        'colorama;os_name == "nt"',
        [],
        ['platform_system=="Windows"'],
    )
    is_same_pkg_and_qualifiers = pin_left < pin_right_0
    assert is_same_pkg_and_qualifiers is False

    # For purposes of sorting -- pkg_name same, qualifiers different
    pin_right_1 = PinDatum(
        abspath_file_left,
        "colorama",
        'colorama;os_name == "nt"',
        [],
        ['python_version<"3.11"'],
    )
    is_same_pkg_qualifiers_differ = pin_left < pin_right_1
    assert isinstance(is_same_pkg_qualifiers_differ, bool)
    # '; platform_system=="Windows"' < '; python_version<"3.11"'
    assert is_same_pkg_qualifiers_differ is True


def test_in_generic(
    tmp_path,
    path_project_base,
    prepare_folders_files,
    prep_pyproject_toml,
):
    """Generic __contains__ implementation"""
    # pytest --showlocals --log-level INFO -k "test_in_generic" tests
    path_cwd = path_project_base()
    venv_path = ".venv"
    dest_relpath = "requirements/pip-tools.in"
    abspath_file_src = cast(
        "Path", resolve_joinpath(path_cwd, "requirements/pip-tools.in")
    )
    path_pyproject_toml = Path(__file__).parent.joinpath(
        "_req_files",
        "venvs_minimal.pyproject_toml",
    )

    loader = None
    with pytest.raises(MissingPackageBaseFolder):
        Ins(loader, venv_path)

    # prepare
    #    pyproject.toml
    path_dest_pyproject_toml = prep_pyproject_toml(path_pyproject_toml, tmp_path)
    loader = VenvMapLoader(path_dest_pyproject_toml.as_posix())

    #    venv and requirements folders
    prep_these = (
        ".venv/.python-version",
        ".tools/.python-version",
        "requirements/deleteme.txt",
        "docs/deleteme.txt",
    )
    prepare_folders_files(prep_these, tmp_path)

    # requirements
    abspath_dest = cast("Path", resolve_joinpath(tmp_path, dest_relpath))
    shutil.copy(abspath_file_src, abspath_dest)

    fpins_0 = FilePins(abspath_dest)
    ins_0 = Ins(loader, venv_path)
    ins_0._file_pins = list()
    ins_0.files = fpins_0

    # InFileType.__eq__
    assert InFileType.FILES != InFileType.ZEROES
    is_files_type = InFileType.FILES
    assert InFileType.FILES == is_files_type

    # Ins.file_abspath
    is_in = in_generic(
        ins_0,
        abspath_dest,
        "file_abspath",
        set_name=InFileType.FILES,
        is_abspath_ok=True,
    )
    assert is_in is True

    is_in = in_generic(
        ins_0,
        abspath_dest,
        "file_abspath",
        set_name=InFileType.ZEROES,
        is_abspath_ok=True,
    )
    assert is_in is False

    # set_name is nonsense. Default InFileType.FILES
    invalids = (
        None,
        1.234,
    )
    for invalid in invalids:
        is_in = in_generic(
            ins_0,
            abspath_dest,
            "file_abspath",
            set_name=invalid,
            is_abspath_ok=True,
        )
        assert is_in is True

    """is_abspath_ok is nonsense --> False. This is not normal usage
    passing in relative path instead of absolute path"""
    invalids = (
        None,
        1.234,
    )
    for invalid in invalids:
        is_in = in_generic(
            ins_0,
            dest_relpath,
            "file_abspath",
            set_name=invalid,
            is_abspath_ok=invalid,
        )
        assert is_in is False


def test_pprint_pindatum(path_project_base):
    """Create a set of PinDatum to pprint"""
    # pytest --showlocals --log-level INFO -k "test_pprint_pindatum" tests
    path_f = Path(__file__).parent.joinpath(
        "_qualifier_conflicts",
        "qualifier_1.unlock",
    )

    # prepare
    set_pins = set()
    pin_colorama = PinDatum(
        path_f,
        "colorama",
        'colorama>=0.4.5 ;platform_system=="Windows"',
        [">=0.4.5"],
        ['platform_system=="Windows"'],
    )

    pin_pip = PinDatum(
        path_f,
        "pip",
        "pip>=24.2",
        [">=24.2"],
        [],
    )

    # has_qualifiers
    t_qualifiers = (
        (pin_colorama, True),
        (pin_pip, False),
    )
    for pin, qualifiers_expected in t_qualifiers:
        assert has_qualifiers(pin.qualifiers) is qualifiers_expected

    set_pins.add(pin_colorama)
    set_pins.add(pin_pip)

    # act
    valids = (
        set_pins,
        list(set_pins),
        tuple(set_pins),
    )
    for valid in valids:
        str_pretty = pprint_pins(set_pins)
        # verify
        assert isinstance(str_pretty, str)


testdata_is_pin = (
    (
        "typing-extensions",
        '''typing-extensions; python_version<"3.10"''',
        [],
        ['''; python_version<"3.10"'''],
        does_not_raise(),
        False,
    ),
    (
        "tomli",
        '''tomli>=2.0.2; python_version<"3.11"''',
        [">=2.0.2"],
        ['''; python_version<"3.11"'''],
        does_not_raise(),
        True,
    ),
    (
        "pip",
        "pip>=24.2",
        [">=24.2"],
        [],
        does_not_raise(),
        True,
    ),
    (
        "isort",
        "isort",
        [],
        [],
        does_not_raise(),
        False,
    ),
)
ids_is_pin = (
    "Not a pin, but has qualifiers",
    "pin and has qualifiers",
    "nudge pin",
    "just a normal package. No package version nor qualifiers",
)


@pytest.mark.parametrize(
    "pkg_name, line, specifiers, qualifiers_expected, expectation, expected_is_pin",
    testdata_is_pin,
    ids=ids_is_pin,
)
def test_is_pin(
    pkg_name,
    line,
    specifiers,
    qualifiers_expected,
    expectation,
    expected_is_pin,
):
    """Defines whats a pin and whats not. Qualifiers is not enough."""
    # pytest --showlocals --log-level INFO -k "test_is_pin" tests
    # act
    file_abspath = Path(__file__).parent.joinpath(
        "_qualifier_conflicts",
        "qualifier_1.unlock",
    )

    with expectation:
        pin = PinDatum(file_abspath, pkg_name, line, specifiers, qualifiers_expected)

    if isinstance(expectation, does_not_raise):
        # verify
        actual_is_pin = is_pin(pin.specifiers)
        assert actual_is_pin is expected_is_pin


testdata_outlastsuffix = (
    (
        OutLastSuffix.LOCK,
        SUFFIX_LOCKED,
        True,
    ),
    (
        OutLastSuffix.UNLOCK,
        SUFFIX_UNLOCKED,
        False,
    ),
)
ids_outlastsuffix = (
    "lock",
    "unlock",
)


@pytest.mark.parametrize(
    "enum_item, str_item_expected, is_lock_expected",
    testdata_outlastsuffix,
    ids=ids_outlastsuffix,
)
def test_outlastsuffix(enum_item, str_item_expected, is_lock_expected):
    """Exercise OutLastSuffix"""
    # pytest --showlocals --log-level INFO -k "test_outlastsuffix" tests
    str_value_actual = str(enum_item)
    assert str_value_actual == str_item_expected
    is_lock_actual = enum_item == OutLastSuffix.LOCK
    assert is_lock_actual is is_lock_expected
