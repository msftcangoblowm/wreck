"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Unit test -- Module

.. code-block:: shell

   python -m coverage run --source='wreck.lock_filepins' -m pytest \
   --showlocals tests/test_lock_filepins.py && coverage report \
   --data-file=.coverage --include="**/lock_filepins.py"

"""

import operator
from collections.abc import Sequence
from contextlib import nullcontext as does_not_raise
from pathlib import (
    Path,
    PurePath,
)
from typing import cast

import pytest

from wreck._safe_path import resolve_joinpath
from wreck.constants import (
    SUFFIX_IN,
    SUFFIX_LOCKED,
    SUFFIX_UNLOCKED,
    g_app_name,
)
from wreck.exceptions import (
    MissingPackageBaseFolder,
    MissingRequirementsFoldersFiles,
)
from wreck.lock_datum import PinDatum
from wreck.lock_filepins import (
    FilePins,
    get_path_cwd,
)
from wreck.lock_util import replace_suffixes_last
from wreck.pep518_venvs import VenvMapLoader

testdata_get_path_cwd_exception = (
    (
        None,
        pytest.raises(MissingPackageBaseFolder),
    ),
    (
        1.234,
        pytest.raises(MissingPackageBaseFolder),
    ),
)
ids_get_path_cwd_exception = (
    "unsupported type None",
    "unsupported type float",
)


@pytest.mark.parametrize(
    "loader, expectation",
    testdata_get_path_cwd_exception,
    ids=ids_get_path_cwd_exception,
)
def test_get_path_cwd_exception(
    loader,
    expectation,
):
    """Real loader not supplied. Test of bad input."""
    # pytest -vv --showlocals --log-level INFO -k "test_get_path_cwd_exception" tests
    with expectation:
        get_path_cwd(loader)


def test_get_path_cwd_normal(
    path_project_base,
):
    """Demonstrate wreck package pyproject.toml is not cwd."""
    # pytest -vv --showlocals --log-level INFO -k "test_get_path_cwd_normal" tests
    path_cwd_actual = path_project_base()

    # reverse search for the pyproject.toml file
    # possible exceptions FileNotFoundError LookupError
    cwd_abspath = str(path_cwd_actual)
    loader = VenvMapLoader(cwd_abspath)
    venvs_relpath = loader.venv_relpaths
    assert isinstance(venvs_relpath, Sequence)
    assert len(venvs_relpath) != 0

    # prepare
    """    using wreck pyproject.toml which definitely exists and
    contains [[tool.wreck.venvs]] sections. No need to copy a pyproject.toml
    into tmp_path"""
    pass

    expectation = does_not_raise()
    with expectation:
        path_package_base_folder = get_path_cwd(loader)
    if isinstance(expectation, does_not_raise):
        assert issubclass(type(path_package_base_folder), PurePath)
        assert path_cwd_actual == path_package_base_folder


testdata_pindatum_realistic = (
    (
        Path(__file__).parent.joinpath(
            "_req_files",
            "venvs.pyproject_toml",
        ),
        ".venv",
        (
            "requirements/pip-tools",
            "requirements/pip",
            "requirements/prod",
            "requirements/kit",
            "requirements/tox",
            "requirements/mypy",
            "requirements/manage",
            "requirements/dev",
        ),
    ),
    (
        Path(__file__).parent.joinpath(
            "_req_files",
            "venvs.pyproject_toml",
        ),
        ".venv",
        (
            "requirements/pip-tools",
            "requirements/pip",
            "requirements/prod",
            "requirements/kit",
            "requirements/tox",
            "requirements/mypy",
            "requirements/manage",
            "requirements/dev",
        ),
    ),
)
ids_pindatum_realistic = (
    "Parse venv requirements files into Pins",
    "importlib-metadata unsynced see prod.lock and dev.lock",
)


@pytest.mark.logging_package_name(g_app_name)
@pytest.mark.parametrize(
    "path_config, venv_path, bases_relpath",
    testdata_pindatum_realistic,
    ids=ids_pindatum_realistic,
)
def test_pindatum_realistic(
    path_config,
    venv_path,
    bases_relpath,
    tmp_path,
    prep_pyproject_toml,
    prepare_folders_files,
    logging_strict,
):
    """test FilePins."""
    # pytest -vv --showlocals --log-level INFO -k "test_pindatum_realistic" tests
    t_two = logging_strict()
    logger, loggers = t_two

    # prepare
    #    pyproject.toml or [something].pyproject_toml
    path_dest_config = prep_pyproject_toml(path_config, tmp_path)
    #    Careful path must be a str
    loader = VenvMapLoader(path_dest_config.as_posix())

    #    venv folder must exist. other [[tool.wreck.venvs]] venv folders need not exist
    venvs_path = (Path(venv_path).joinpath(".python-version"),)
    prepare_folders_files(venvs_path, tmp_path)

    #    requirements empty files and folders; no .unlock or .lock files
    seq_rel_paths = (
        ".doc/.venv/.python-version",
        ".venv/.python-version",
        "requirements/pins.shared.in",
        "docs/requirements.in",
        "requirements/dev.in",
    )
    prepare_folders_files(seq_rel_paths, tmp_path)
    abspath_pins_shared_in = cast("Path", resolve_joinpath(tmp_path, seq_rel_paths[2]))
    abspath_pins_docs_requirements_in = cast(
        "Path",
        resolve_joinpath(
            tmp_path,
            "docs/requirements.in",
        ),
    )
    abspath_dev_in = cast(
        "Path",
        resolve_joinpath(
            tmp_path,
            "requirements/dev.in",
        ),
    )

    # verify -- unsupported file extension. Not in (.in, .lock, .unlock)
    abspath_pins_shared_nonsense = replace_suffixes_last(
        abspath_pins_shared_in, ".nonsense"
    )
    with pytest.raises(ValueError):
        FilePins(abspath_pins_shared_nonsense)
    # verify -- nonexistent requirement file --> MissingRequirementsFoldersFiles
    abspath_dogfood_in = cast(
        "Path",
        resolve_joinpath(
            tmp_path,
            f"requirements/dogfood{SUFFIX_IN}",
        ),
    )
    with pytest.raises(MissingRequirementsFoldersFiles):
        FilePins(abspath_dogfood_in)

    # act
    #    FilePins append a PinDatum (package pip)
    #    dest [abspath]/requirements/pins.shared.in
    fpins = FilePins(abspath_pins_shared_in)
    fpins_before_actual = len(fpins)
    pindatum_pip = PinDatum(
        abspath_pins_shared_in,
        "pip",
        '"pip<24.2; python_version < "3.10"',
        ["<24.2"],
        ['python_version < "3.10"'],
    )
    pins = fpins._pins
    #    Save a requirement
    fpins.packages_save_to_parent((), ("requirement/pin.shared.in",))

    pins.append(pindatum_pip)
    fpins._pins = pins
    fpins._iter = iter(fpins._pins)
    fpins_after_actual = len(fpins)
    assert fpins_after_actual == fpins_before_actual + 1

    #    FilePins.__repr__
    repr_fpins = repr(fpins)
    assert isinstance(repr_fpins, str)

    #    FilePins.__hash__ and FilePins.__eq__
    int_hash_left = hash(fpins)
    assert isinstance(int_hash_left, int)
    right = fpins.file_abspath
    int_hash_right = hash((right,))
    assert int_hash_left == int_hash_right

    #    Path abspath
    assert issubclass(type(right), PurePath)
    assert operator.eq(fpins, right) is True
    assert fpins.__eq__(right)
    assert fpins == right
    #    str abspath
    assert fpins == str(right)
    #    None
    assert fpins is not None
    #    unsupported type
    assert fpins != 4

    #    FilePins.__lt__ (to support sorted)
    #    unsupported types
    invalids = (
        None,
        1.234,
    )
    for invalid in invalids:
        with pytest.raises(TypeError):
            operator.lt(fpins, invalid)

    #    FilePins.__contains__
    assert pindatum_pip in fpins
    assert None not in fpins
    assert 3 not in fpins

    #    FilePins.depth property
    assert fpins.depth == 0

    #    FilePins.relpath
    with pytest.raises(MissingPackageBaseFolder):
        fpins.relpath(None)
    fpins.relpath(loader).as_posix() == "requirements/pins.shared.in"

    # FilePins.by_pkg
    lst_out = fpins.by_pkg(None)
    assert isinstance(lst_out, list)
    assert len(lst_out) == 0
    lst_out = fpins.by_pkg("pip")
    assert isinstance(lst_out, list)
    assert len(lst_out) == 1

    # FilePins.by_pin_or_qualifier
    gen = fpins.by_pin_or_qualifier()
    lst_pins_notable = list(gen)
    lst_pins_notable_count = len(lst_pins_notable)
    assert lst_pins_notable_count != 0

    # Loop Iterator
    for pin_found in fpins:
        assert isinstance(pin_found, PinDatum)

    # Loop Iterator again; the magic reusable Iterator!
    for pin_found in fpins:
        assert isinstance(pin_found, PinDatum)

    # Failing here under Windows. See what is happening inside the function
    """
    from logging_strict.tech_niques import get_locals_dynamic  # noqa: F401
    args = (loader, venv_path)
    kwargs = {"suffix": None, "filter_by_pin": None}
    t_ret = get_locals_dynamic(_wrapper_pins_by_pkg, *args, **kwargs)  # noqa: F841
    """

    # Reorganize Pin by pkgname. Need to prepare .lock file
    #    suffix None --> .lock, filter_by_pin None --> True
    pindatum_by_pkg = fpins.by_pkg("pip")
    assert isinstance(pindatum_by_pkg, list)
    assert isinstance(list(pindatum_by_pkg)[0], PinDatum)

    # prepare
    #    requirements empty files and folders
    suffixes = (SUFFIX_IN, SUFFIX_UNLOCKED, SUFFIX_LOCKED)
    seq_rel_paths = []
    for suffix in suffixes:
        for base_path in bases_relpath:
            seq_rel_paths.append(f"{base_path}{suffix}")
    prepare_folders_files(seq_rel_paths, tmp_path)

    # act
    #    same type (FilePins)
    # fpins_right_0 = FilePins(abspath_dest_in)
    fpins_right_0 = FilePins(abspath_dev_in)
    assert fpins != fpins_right_0
    #    Same folder (requirements/dev.in < requirements/pin.shared.in)
    assert fpins_right_0 < fpins
    #    different folder
    fpins_right_1 = FilePins(abspath_pins_docs_requirements_in)
    is_left_greater = fpins > fpins_right_1
    assert is_left_greater


testdata_filepins_resolve = (
    (
        Path(__file__).parent.parent.joinpath(
            "docs",
            "pip-tools.in",
        ),
        "../requirements/pins.shared.in",
    ),
)
ids_filepins_resolve = ("Resolve",)


@pytest.mark.parametrize(
    "abspath_f, constraint_relpath",
    testdata_filepins_resolve,
    ids=ids_filepins_resolve,
)
def test_filepins_resolve(
    abspath_f,
    constraint_relpath,
):
    """Read a FilePins. Resolve, from a set, discards a constraint."""
    # pytest -vv --showlocals --log-level INFO -k "test_filepins_resolve" tests
    fpins_0 = FilePins(abspath_f)
    # nonexistent FilePins attribute, plural --> AssertionError
    with pytest.raises(AssertionError):
        fpins_0.resolve(constraint_relpath, plural="dogfood")

    # nonsense singular --> 'constraint'
    fpins_0.resolve(constraint_relpath, singular="dogfood")
