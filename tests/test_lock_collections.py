"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Unit test -- Module

.. code-block:: shell

   python -m coverage run --source='wreck.lock_collections' -m pytest \
   --showlocals tests/test_lock_collections.py && coverage report \
   --data-file=.coverage --include="**/lock_collections.py"

"""

import shutil
from contextlib import nullcontext as does_not_raise
from pathlib import Path
from typing import cast

import pytest

from wreck._safe_path import resolve_joinpath
from wreck.constants import (
    SUFFIX_IN,
    SUFFIX_LOCKED,
    g_app_name,
)
from wreck.exceptions import MissingRequirementsFoldersFiles
from wreck.lock_collections import Ins
from wreck.lock_compile import lock_compile
from wreck.lock_datum import InFileType
from wreck.lock_filepins import FilePins
from wreck.lock_fixing import Fixing
from wreck.lock_util import replace_suffixes_last
from wreck.pep518_venvs import VenvMapLoader

testdata_why_did_you_do_that = (
    (
        Path(__file__).parent.joinpath("_req_files", "venvs_minimal.pyproject_toml"),
        ".tools",
        ("docs/pip-tools",),
        pytest.raises(MissingRequirementsFoldersFiles),
    ),
    (
        Path(__file__).parent.joinpath("_req_files", "venvs_minimal.pyproject_toml"),
        ".dogfood",
        ("docs/pip-tools",),
        pytest.raises(KeyError),
    ),
)
ids_why_did_you_do_that = (
    "missing support requirement files",
    "no such venv",
)


@pytest.mark.parametrize(
    "path_config, venv_relpath, req_files, expectation",
    testdata_why_did_you_do_that,
    ids=ids_why_did_you_do_that,
)
def test_why_did_you_do_that(
    path_config,
    venv_relpath,
    req_files,
    expectation,
    tmp_path,
    path_project_base,
    prepare_folders_files,
    prep_pyproject_toml,
):
    """venv relpath is not supposed to be an absolute path."""
    # pytest --showlocals --log-level INFO -k "test_why_did_you_do_that" tests
    path_cwd = path_project_base()
    abspath_venv = cast("Path", resolve_joinpath(tmp_path, venv_relpath))
    seq_base_dir = (
        str(Path(venv_relpath).joinpath(".python-version")),
        str(Path("requirements").joinpath("empty.txt")),
        str(Path("docs").joinpath("empty.txt")),
    )

    # prepare
    #    pyproject.toml
    abspath_config_dest = prep_pyproject_toml(path_config, tmp_path)
    config_dest_abspath = str(abspath_config_dest)

    #    folders
    prepare_folders_files(seq_base_dir, tmp_path)

    #    requirements files -- direct and maybe support files
    for req_relpath_src in req_files:
        abspath_src = cast("Path", resolve_joinpath(path_cwd, req_relpath_src))
        abspath_src_in = cast(
            "Path",
            resolve_joinpath(
                abspath_src.parent,
                f"{abspath_src.name}{SUFFIX_IN}",
            ),
        )
        src_in_abspath = str(abspath_src_in)
        abspath_dest = cast("Path", resolve_joinpath(tmp_path, req_relpath_src))
        abspath_dest_in = cast(
            "Path",
            resolve_joinpath(
                abspath_dest.parent,
                f"{abspath_dest.name}{SUFFIX_IN}",
            ),
        )
        shutil.copy(src_in_abspath, abspath_dest_in)

    loader = VenvMapLoader(config_dest_abspath)
    #    Will convert abspath_venv --> venv_relpath
    ins = Ins(loader, abspath_venv)
    #    __len__ and __iter__
    assert len(iter(ins)) == 0
    #    __contains__
    assert None not in ins
    assert 7.23 not in ins

    # act
    #    suffix_last .dogfood --> .in then
    #    Did not prepare the requirements files --> MissingRequirementsFoldersFiles
    with expectation:
        ins.load(suffix_last=".dogfood")


testdata_ins_realistic = (
    (
        Path(__file__).parent.joinpath(
            "_req_files",
            "venvs.pyproject_toml",
        ),
        ".venv",
        (
            (
                Path(__file__).parent.parent.joinpath(
                    "requirements",
                    "dev.in",
                ),
                "requirements/dev.in",
            ),
        ),
        (
            (
                Path(__file__).parent.parent.joinpath(
                    "requirements",
                    "prod.in",
                ),
                "requirements/prod.in",
            ),
            (
                Path(__file__).parent.parent.joinpath(
                    "requirements",
                    "pins.shared.in",
                ),
                "requirements/pins.shared.in",
            ),
            (
                Path(__file__).parent.parent.joinpath(
                    "requirements",
                    "pins-cffi.in",
                ),
                "requirements/pins-cffi.in",
            ),
            (
                Path(__file__).parent.parent.joinpath(
                    "requirements",
                    "pins-validate-pyproject-pep639.in",
                ),
                "requirements/pins-validate-pyproject-pep639.in",
            ),
        ),
        (
            ".venv/.python-version",
            ".doc/.venv/.python-version",
            "requirements/pins.shared.in",
            "requirements/pins-typing.in",
        ),
        (
            "docs/pip-tools",
            "docs/requirements",
            "requirements/pip-tools",
            "requirements/pip",
            "requirements/prod",
            "requirements/kit",
            "requirements/tox",
            "requirements/mypy",
            "requirements/manage",
            "requirements/dev",
        ),
        does_not_raise(),
        8,
        4,
    ),
    (
        Path(__file__).parent.joinpath(
            "_req_files",
            "venvs.pyproject_toml",
        ),
        ".venv",
        (
            (
                Path(__file__).parent.parent.joinpath(
                    "requirements",
                    "dev.in",
                ),
                "requirements/dev.in",
            ),
        ),
        (
            (
                Path(__file__).parent.parent.joinpath(
                    "requirements",
                    "prod.in",
                ),
                "requirements/prod.in",
            ),
            (
                Path(__file__).parent.parent.joinpath(
                    "requirements",
                    "pins.shared.in",
                ),
                "requirements/pins.shared.in",
            ),
        ),
        (
            ".venv/.python-version",
            ".doc/.venv/.python-version",
            "requirements/pins.shared.in",
            "requirements/pins-typing.in",
        ),
        (
            "docs/pip-tools",
            "docs/requirements",
            "requirements/pip-tools",
            "requirements/pip",
            "requirements/prod",
            "requirements/kit",
            "requirements/tox",
            "requirements/mypy",
            "requirements/manage",
            "requirements/dev",
        ),
        pytest.raises(MissingRequirementsFoldersFiles),
        8,
        0,
    ),
    (
        Path(__file__).parent.joinpath(
            "_no_unlock_pins",
            "prod_and_dev.pyproject_toml",
        ),
        ".venv",
        (
            (
                Path(__file__).parent.joinpath(
                    "_no_unlock_pins",
                    "prod.in",
                ),
                "requirements/prod.in",
            ),
        ),
        (
            (
                Path(__file__).parent.joinpath(
                    "_no_unlock_pins",
                    "dev.in",
                ),
                "requirements/dev.in",
            ),
            (
                Path(__file__).parent.joinpath(
                    "_no_unlock_pins",
                    "pins-tomli.in",
                ),
                "requirements/pins-tomli.in",
            ),
        ),
        (
            ".venv/.python-version",
            "requirements/pins-tomli.in",
        ),
        (
            "requirements/prod",
            "requirements/dev",
            "requirements/pins-tomli",
        ),
        does_not_raise(),
        2,
        2,
    ),
    (
        Path(__file__).parent.joinpath(
            "_no_unlock_pins",
            "prod_and_dev.pyproject_toml",
        ),
        ".venv",
        (
            (
                Path(__file__).parent.joinpath(
                    "_no_unlock_pins",
                    "dev.in",
                ),
                "requirements/dev.in",
            ),
        ),
        (
            (
                Path(__file__).parent.joinpath(
                    "_no_unlock_pins",
                    "support.in",
                ),
                "requirements/support.in",
            ),
        ),
        (
            ".venv/.python-version",
            "requirements/dev.in",
        ),
        (
            "requirements/dev",
            "requirements/support",
        ),
        pytest.raises(MissingRequirementsFoldersFiles),
        2,
        0,
    ),
)
ids_ins_realistic = (
    "Has both requirements and constraints",
    "missing a support file",
    "do not create pins unlock files",
    "-r missing",
)


@pytest.mark.logging_package_name(g_app_name)
@pytest.mark.parametrize(
    (
        "path_config, venv_path, seq_reqs_primary, seq_reqs_support, seq_empties, "
        "req_base_empties, expectation, pkg_pin_count_expected, path_unlocks_expected"
    ),
    testdata_ins_realistic,
    ids=ids_ins_realistic,
)
def test_ins_realistic(
    path_config,
    venv_path,
    seq_reqs_primary,
    seq_reqs_support,
    seq_empties,
    req_base_empties,
    expectation,
    pkg_pin_count_expected,
    path_unlocks_expected,
    tmp_path,
    prep_pyproject_toml,
    prepare_folders_files,
    logging_strict,
):
    """test wreck.lock_collections.Ins"""
    # pytest -vv --showlocals --log-level INFO -k "test_ins_realistic" tests
    # pytest -vv --showlocals --log-level INFO tests/test_lock_collections.py::test_ins_realistic\[Has\ both\ requirements\ and\ constraints\] tests
    # pytest -vv --showlocals --log-level INFO tests/test_lock_collections.py::test_ins_realistic\[do\ not\ create\ pins\ unlock\ files\] tests
    t_two = logging_strict()
    logger, loggers = t_two

    # prepare
    #    pyproject.toml or [something].pyproject_toml
    path_dest_config = prep_pyproject_toml(path_config, tmp_path)

    #    venv folders must exist. This fixture creates files. So .python-version
    #    requirements empty files and folders; no .unlock or .lock files
    prepare_folders_files(seq_empties, tmp_path)

    loader = VenvMapLoader(path_dest_config.as_posix())

    #    requirements empty files and folders
    suffixes = (SUFFIX_IN, SUFFIX_LOCKED)
    rel_paths = []
    for suffix in suffixes:
        for base_path in req_base_empties:
            rel_paths.append(f"{base_path}{suffix}")
    prepare_folders_files(rel_paths, tmp_path)

    for t_paths in seq_reqs_primary:
        src_abspath, dest_relpath = t_paths

        #    overwrite 'requirements/dev.in'
        abspath_dest = cast("Path", resolve_joinpath(tmp_path, dest_relpath))

        shutil.copy(src_abspath, abspath_dest)

        #    pip-compile -o [file].lock [file].in
        #    careful no .shared
        src_abspath_lock = replace_suffixes_last(src_abspath, SUFFIX_LOCKED)
        abspath_dest_lock = replace_suffixes_last(abspath_dest, SUFFIX_LOCKED)
        #    not stopping if missing primary is so can cause MissingRequirementsFoldersFiles
        if src_abspath_lock.exists():
            shutil.copy(src_abspath_lock, abspath_dest_lock)

    is_first = True
    for t_paths in seq_reqs_support:
        src_abspath, dest_relpath = t_paths

        #    overwrite 'requirements/dev.in'
        abspath_dest = cast("Path", resolve_joinpath(tmp_path, dest_relpath))

        if is_first:
            is_first = False
            abspath_dest_0 = abspath_dest

        shutil.copy(src_abspath, abspath_dest)

    with expectation:
        # Normally would call --> wreck.lock_fixing.fix_requirements_lock
        pass

        # Create .lock files
        #    Runs pip-compile. The target venv will contain the
        #    correct python interpreter
        lock_compile(loader, venv_path)
        # Fix .lock files
        Fixing.fix_requirements_lock(loader, venv_path)
        # Read .in files once
        ins = Ins(loader, venv_path)
        ins.load(suffix_last=None)
    if isinstance(expectation, does_not_raise):
        repr_ins = repr(ins)
        assert isinstance(repr_ins, str)

        pkg_ins_count_actual = len(ins)
        fpins_abspath = [fpin.file_abspath for fpin in ins._file_pins]
        msg_mismatch = f"expected count doesn't match filepins {fpins_abspath}"
        assert pkg_ins_count_actual == pkg_pin_count_expected, msg_mismatch

        #    Loop Iterator
        for fpins in ins:
            assert isinstance(fpins, FilePins)

        #    Loop Iterator again; the magic reusable Iterator!
        for fpins in ins:
            assert isinstance(fpins, FilePins)

        fpin_maybe = ins.get_by_abspath(abspath_dest_0, set_name=InFileType.ZEROES)
        assert fpin_maybe is not None
        assert isinstance(fpin_maybe, FilePins)
        #    __contains__
        assert fpin_maybe in ins

        invalids = (
            None,
            1.234,
        )
        for invalid in invalids:
            #    not a InFileType
            fpin_maybe = ins.get_by_abspath(abspath_dest_0, set_name=invalid)
            assert fpin_maybe is None
            #    invalid abspath_dest_0 --> ValueError
            with pytest.raises(ValueError):
                ins.get_by_abspath(invalid, set_name=InFileType.ZEROES)

        # Write .unlock files
        """Should confirm contains own and ancestors packages.

        These files are skipped and will not produce a .unlock file

        - ``.shared.in`` files starting with ``pin``

        """
        gen = ins.write()
        path_unlocks = list(gen)
        path_unlocks_actual = len(path_unlocks)
        assert path_unlocks_actual == path_unlocks_expected
        # Fixing.fix_unlock
        #    Would fix the unlock files using knowledge gleened from
        #    .lock pin version discrepancies
        pass


testdata_duplicate_lines = (
    (
        Path(__file__).parent.joinpath(
            "_duplicate_line",
            "prod_and_dev.pyproject_toml",
        ),
        ".venv",
        (
            (
                Path(__file__).parent.joinpath(
                    "_duplicate_line",
                    "dev.in",
                ),
                "requirements/dev.in",
            ),
            (
                Path(__file__).parent.joinpath(
                    "_duplicate_line",
                    "prod.in",
                ),
                "requirements/prod.in",
            ),
        ),
        (
            (
                Path(__file__).parent.joinpath(
                    "_duplicate_line",
                    "dev.unlock",
                ),
                "requirements/dev.unlock",
            ),
        ),
        "logging-strict>=1.5.0",
        1,
    ),
)
ids_duplicate_lines = ("in dev.unlock expect one line not two",)


@pytest.mark.parametrize(
    (
        "path_config, venv_path, seq_reqs_primary, seq_reqs_support, "
        "pattern, num_lines_expected"
    ),
    testdata_duplicate_lines,
    ids=ids_duplicate_lines,
)
@pytest.mark.logging_package_name(g_app_name)
def test_duplicate_lines(
    path_config,
    venv_path,
    seq_reqs_primary,
    seq_reqs_support,
    pattern,
    num_lines_expected,
    tmp_path,
    prep_pyproject_toml,
    prepare_folders_files,
):
    """Verify .unlock duplicate lines removed.

    **Could not reproduce the cause**, instead

    - start with a ``dev.unlock`` with duplicate lines

    - Read the dev.unlock

    - write it out

    .. seealso::

       ``tests/_duplicate_line/README.rst``

    """
    # pytest -vv --showlocals --log-level INFO -k "test_duplicate_lines" tests
    # prepare
    #    pyproject.toml or [something].pyproject_toml
    path_dest_config = prep_pyproject_toml(path_config, tmp_path)

    #    venv folders must exist. This fixture creates files. So .python-version
    venvs_path = (
        ".venv/.python-version",
        "requirements/README.rst",
    )
    prepare_folders_files(venvs_path, tmp_path)

    #    secondary support files
    is_first = True
    for t_paths in seq_reqs_support:
        src_abspath, dest_relpath = t_paths

        #    overwrite 'requirements/dev.in'
        abspath_dest = cast("Path", resolve_joinpath(tmp_path, dest_relpath))

        if is_first:
            is_first = False
            abspath_dest_0 = abspath_dest

        shutil.copy(src_abspath, abspath_dest)

    # primary .in files
    for t_paths in seq_reqs_primary:
        src_abspath, dest_relpath = t_paths

        #    overwrite 'requirements/dev.in'
        abspath_dest = cast("Path", resolve_joinpath(tmp_path, dest_relpath))

        shutil.copy(src_abspath, abspath_dest)

    expectation = does_not_raise()
    with expectation:
        loader = VenvMapLoader(path_dest_config.as_posix())
        ins = Ins(loader, venv_path)
        ins.load(suffix_last=None)
    if isinstance(expectation, does_not_raise):
        gen = ins.write()
        list(gen)

        # Verify
        #    dev.unlock line count -- only lines matching pattern
        num_lines_actual = sum(
            1 for line in abspath_dest_0.open() if line.strip() == pattern
        )
        assert num_lines_actual == num_lines_expected
