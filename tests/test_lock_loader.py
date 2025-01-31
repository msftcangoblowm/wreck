"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Unit test -- Module

.. code-block:: shell

   python -m coverage run --source='wreck.lock_loader' -m pytest \
   --showlocals tests/test_lock_loader.py && coverage report \
   --data-file=.coverage --include="**/lock_loader.py"

"""

import shutil
from contextlib import nullcontext as does_not_raise
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from pip_requirements_parser import InstallationError

from wreck._safe_path import resolve_joinpath
from wreck.constants import (
    SUFFIX_IN,
    SUFFIX_LOCKED,
    SUFFIX_UNLOCKED,
    g_app_name,
)
from wreck.exceptions import MissingRequirementsFoldersFiles
from wreck.lock_loader import (
    LoaderPinDatum,
    _check_filter_by_pin,
)
from wreck.lock_util import replace_suffixes_last
from wreck.pep518_venvs import VenvMapLoader

testdata_loader_pindatum = (
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
                    "dev.unlock",
                ),
                "requirements/dev.in",
            ),
            (
                Path(__file__).parent.parent.joinpath(
                    "requirements",
                    "prod.unlock",
                ),
                "requirements/prod.in",
            ),
        ),
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
            (
                Path(__file__).parent.parent.joinpath(
                    "requirements",
                    "dev.in",
                ),
                "requirements/dev.in",
            ),
            (
                Path(__file__).parent.parent.joinpath(
                    "requirements",
                    "prod.unlock",
                ),
                "requirements/prod.in",
            ),
        ),
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
ids_loader_pindatum = (
    "Parse venv requirements files into Pins",
    "has two constraints and a requirement",
)


@pytest.mark.logging_package_name(g_app_name)
@pytest.mark.parametrize(
    "path_config, venv_path, seq_reqs, bases_relpath",
    testdata_loader_pindatum,
    ids=ids_loader_pindatum,
)
def test_loader_pindatum(
    path_config,
    venv_path,
    seq_reqs,
    bases_relpath,
    tmp_path,
    prep_pyproject_toml,
    prepare_folders_files,
    logging_strict,
):
    """test FilePins."""
    # pytest -vv --showlocals --log-level INFO -k "test_loader_pindatum" tests
    t_two = logging_strict()
    logger, loggers = t_two

    # prepare
    #    pyproject.toml or [something].pyproject_toml
    path_dest_config = prep_pyproject_toml(path_config, tmp_path)
    #    Careful path must be a str
    loader = VenvMapLoader(path_dest_config.as_posix())
    path_base_dir = loader.project_base

    #     requirements folders
    venvs_path = (
        "requirements/empty.txt",
        "docs/empty.txt",
    )
    prepare_folders_files(venvs_path, tmp_path)

    #    requirements empty files and folders
    suffixes = (SUFFIX_IN, SUFFIX_UNLOCKED, SUFFIX_LOCKED)
    seq_rel_paths = []
    for suffix in suffixes:
        for base_path in bases_relpath:
            seq_rel_paths.append(f"{base_path}{suffix}")
    prepare_folders_files(seq_rel_paths, tmp_path)

    # Other venv, requirement files not prepared
    with pytest.raises(NotADirectoryError):
        LoaderPinDatum()(
            loader,
            venv_path,
            suffix=SUFFIX_UNLOCKED,
            filter_by_pin=None,
        )

    #    venv folder must exist. other [[tool.wreck.venvs]] venv folders need not exist
    venvs_path = (
        ".doc/.venv/.python-version",
        ".venv/.python-version",
    )
    prepare_folders_files(venvs_path, tmp_path)

    # Other venv, requirement files not prepared
    # pytest.raises(MissingRequirementsFoldersFiles)
    expectation = does_not_raise()
    with expectation:
        LoaderPinDatum()(
            loader,
            venv_path,
            suffix=SUFFIX_UNLOCKED,
            filter_by_pin=None,
        )

    #    support files
    seq_rel_paths = (
        "requirements/pins.shared.in",
        "docs/requirements.in",
        "docs/pip-tools.in",
    )
    prepare_folders_files(seq_rel_paths, tmp_path)

    #    requirements empty files and folders
    suffixes = (SUFFIX_IN, SUFFIX_UNLOCKED, SUFFIX_LOCKED)
    seq_rel_paths = []
    for suffix in suffixes:
        for base_path in bases_relpath:
            seq_rel_paths.append(f"{base_path}{suffix}")
    prepare_folders_files(seq_rel_paths, tmp_path)

    for t_paths in seq_reqs:
        src_abspath, dest_relpath = t_paths

        #    overwrite 'requirements/dev.unlock'
        abspath_dest = cast("Path", resolve_joinpath(tmp_path, dest_relpath))
        abspath_dest_in = replace_suffixes_last(abspath_dest, suffix_last=SUFFIX_IN)
        shutil.copy(src_abspath, abspath_dest_in)

        #    pip-compile -o [file].lock [file].unlock
        #    careful no .shared
        src_abspath_lock = replace_suffixes_last(src_abspath, SUFFIX_LOCKED)
        abspath_dest_lock = replace_suffixes_last(abspath_dest_in, SUFFIX_LOCKED)
        shutil.copy(src_abspath_lock, abspath_dest_lock)

    # Cause pip_requirements_parser.RequirementsFile.from_file to fail
    with patch(
        "pip_requirements_parser.RequirementsFile.from_file",
        side_effect=InstallationError,
    ):
        with pytest.raises(MissingRequirementsFoldersFiles):
            LoaderPinDatum()(
                loader,
                venv_path,
                suffix=SUFFIX_UNLOCKED,
                filter_by_pin=None,
            )

    # act
    #    absolute path venv
    abspath_venv = cast("Path", resolve_joinpath(path_base_dir, venv_path))
    set_pins_autofixed = LoaderPinDatum()(
        loader,
        abspath_venv,
        suffix=SUFFIX_IN,
        filter_by_pin=None,
    )
    # verify
    assert isinstance(set_pins_autofixed, set)
    assert len(set_pins_autofixed) != 0

    # act
    #    filter by pin True and .lock file
    set_pindatum_0 = LoaderPinDatum()(
        loader,
        venv_path,
        suffix=SUFFIX_LOCKED,
        filter_by_pin=True,
    )
    # verify
    is_there_will_be_pins = len(set_pindatum_0) != 0
    assert is_there_will_be_pins is True

    # act
    #    filter by pin False and .lock file
    set_pindatum_0 = LoaderPinDatum()(
        loader,
        venv_path,
        suffix=SUFFIX_LOCKED,
        filter_by_pin=False,
    )
    # verify
    is_there_will_be_pins = len(set_pindatum_0) != 0
    assert is_there_will_be_pins is True


testdata_check_filter_by_pin = (
    (None, True),
    (1.234, True),
    (False, False),
    (True, True),
)
ids_check_filter_by_pin = (
    "None --> default",
    "unsupported type --> default",
    "False is valid",
    "True is valid",
)


@pytest.mark.parametrize(
    "val, expected",
    testdata_check_filter_by_pin,
    ids=ids_check_filter_by_pin,
)
def test_check_filter_by_pin(val, expected):
    """Test _check_filter_by_pin"""
    # pytest -vv --showlocals --log-level INFO -k "test_check_filter_by_pin" tests
    actual = _check_filter_by_pin(val)
    assert actual == expected
