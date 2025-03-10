"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

..

Unittest for entrypoint, cli_dependencies

.. code-block:: shell

   python -m coverage run --source='wreck.cli_dependencies' -m pytest \
   --showlocals tests/test_cli_dependencies.py && coverage report \
   --data-file=.coverage --include="**/cli_dependencies.py"

"""

import shutil
import sys
import traceback
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from wreck._safe_path import resolve_joinpath
from wreck.cli_dependencies import (
    entrypoint_name,
    main,
    requirements_fix_v2,
    requirements_unlock,
)
from wreck.constants import (
    SUFFIX_IN,
    g_app_name,
)
from wreck.lock_util import replace_suffixes_last


def test_cli_main():
    """Minimally test package version is printed."""
    runner = CliRunner()
    # --version
    """
    cmd = ["--version"]
    result = runner.invoke(main, cmd)
    assert result.exit_code == 0
    assert "version" in result.stdout
    """

    # --help
    cmd = ["--help"]
    result = runner.invoke(main, cmd)
    assert result.exit_code == 0
    assert f"Command-line for {entrypoint_name}. Prints usage" in result.stdout


test_data_venvmap_loader_exceptions = (
    (
        requirements_fix_v2,
        Path(__file__).parent.joinpath(
            "_bad_files", "section_misspelled.pyproject_toml"
        ),
        ".doc/.venv",
        (
            "requirements/pins.shared.in",
            "requirements/prod.in",
            "docs/pip-tools.in",
            "docs/requirements.in",
        ),
        4,
    ),
    (
        requirements_unlock,
        Path(__file__).parent.joinpath(
            "_bad_files", "section_misspelled.pyproject_toml"
        ),
        ".doc/.venv",
        (
            "requirements/pins.shared.in",
            "requirements/prod.in",
            "docs/pip-tools.in",
            "docs/requirements.in",
        ),
        4,
    ),
)
ids_venvmap_loader_exceptions = (
    "lock no tool.venv section",
    "unlock no tool.venv section",
)


@pytest.mark.logging_package_name(g_app_name)
@pytest.mark.parametrize(
    "fcn, path_pyproject_toml, venv_path, seq_in, expected_exit_code",
    test_data_venvmap_loader_exceptions,
    ids=ids_venvmap_loader_exceptions,
)
def test_venvmap_loader_exceptions(
    fcn,
    path_pyproject_toml,
    venv_path,
    seq_in,
    expected_exit_code,
    tmp_path,
    prep_pyproject_toml,
    logging_strict,
):
    """Test VenvMapLoader exceptions 3 and 4."""
    # pytest -vv --showlocals --log-level INFO -k "test_venvmap_loader_exceptions" tests
    t_two = logging_strict()
    logger, loggers = t_two

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as tmp_dir_path:
        path_tmp_dir = Path(tmp_dir_path)

        cmd = (
            "--path",
            path_tmp_dir,
            "--venv-relpath",
            venv_path,
        )

        # Couldn't find the pyproject.toml file (3)
        result = runner.invoke(fcn, cmd)
        actual_exit_code = 3

        # prepare
        #    pyproject.toml
        prep_pyproject_toml(path_pyproject_toml, path_tmp_dir)

        # In pyproject.toml, expecting sections [[tool.wreck.venvs]]. Create them (4)
        result = runner.invoke(fcn, cmd)
        actual_exit_code = result.exit_code
        assert actual_exit_code == expected_exit_code


testdata_lock_unlock_docs_venv = (
    (
        requirements_unlock,
        Path(__file__).parent.joinpath("_good_files", "complete.pyproject_toml"),
        ".doc/.venv",
        (
            "requirements/pins.shared.in",
            "requirements/prod.in",
            "docs/pip-tools.in",
            "docs/requirements.in",
        ),
        0,
    ),
    (
        requirements_fix_v2,
        Path(__file__).parent.joinpath("_req_files", "venvs_minimal.pyproject_toml"),
        ".tools",
        (
            "requirements/pins.shared.in",
            "docs/pip-tools.in",
        ),
        0,
    ),
    pytest.param(
        requirements_fix_v2,
        Path(__file__).parent.joinpath("_good_files", "complete.pyproject_toml"),
        ".doc/.venv",
        (
            "requirements/prod.in",
            "requirements/pins-cffi.in",
            "requirements/pins.shared.in",
            "docs/pip-tools.in",
            "docs/requirements.in",
        ),
        0,
        marks=pytest.mark.skipif(sys.version_info < (3, 10), reason="Sphinx>=8 <py310"),
    ),
    pytest.param(
        requirements_fix_v2,
        Path(__file__).parent.joinpath("_good_files", "complete.pyproject_toml"),
        ".doc/.venv",
        (
            "requirements/prod.in",
            "requirements/pins-cffi.in",
            "requirements/pins.shared.in",
            "docs/pip-tools.in",
            "docs/requirements.in",
        ),
        1,
        marks=pytest.mark.skipif(sys.version_info > (3, 9), reason="Sphinx>=8 py310+"),
    ),
)
ids_lock_unlock_docs_venv = (
    "unlock for drain-swamp and docs",
    "lock for docs/pip-tools",
    "lock for drain-swamp and docs",
    "lock for drain-swamp and docs. Sphinx>=8 py310+",
)


@pytest.mark.logging_package_name(g_app_name)
@pytest.mark.parametrize(
    "fcn, path_pyproject_toml, venv_path, seq_in, expected_exit_code",
    testdata_lock_unlock_docs_venv,
    ids=ids_lock_unlock_docs_venv,
)
def test_lock_unlock_docs_venv(
    fcn,
    path_pyproject_toml,
    venv_path,
    tmp_path,
    seq_in,
    expected_exit_code,
    prep_pyproject_toml,
    prepare_folders_files,
    path_project_base,
    logging_strict,
):
    """Test dependency lock and unlock."""
    # pytest -vv --showlocals --log-level INFO -k "test_lock_unlock_docs_venv" -v tests
    # pytest --showlocals tests/test_cli_dependencies.py::test_lock_unlock_docs_venv[lock\ for\ drain-swamp\ and\ docs]
    # python [path to project base]src/wreck/cli_dependencies.py unlock --path=[tmp path folder] --venv-relpath='.doc/.venv'
    # python [path to project base]src/wreck/cli_dependencies.py unlock --path=[tmp path folder]
    t_two = logging_strict()
    logger, loggers = t_two

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as tmp_dir_path:
        path_tmp_dir = Path(tmp_dir_path)

        # prepare
        #    pyproject.toml
        prep_pyproject_toml(path_pyproject_toml, path_tmp_dir)
        cmd = (
            "--path",
            path_tmp_dir,
            "--venv-relpath",
            venv_path,
        )

        # Missing venv folders --> NotADirectoryError (7)
        result = runner.invoke(fcn, cmd)
        actual_exit_code = 7

        #    venv folder(s)
        venv_relpaths = (
            ".venv",
            ".tools",
            ".doc/.venv",
            "docs",
        )
        for create_relpath in venv_relpaths:
            abspath_venv = resolve_joinpath(path_tmp_dir, create_relpath)
            abspath_venv.mkdir(parents=True, exist_ok=True)

        # Missing ``.in`` files --> MissingRequirementsFoldersFiles (6)
        result = runner.invoke(fcn, cmd)
        actual_exit_code = 6

        #    requirements folders (and empty files)
        prepare_folders_files(seq_in, path_tmp_dir)

        #    requirements .in (real files)
        path_cwd = path_project_base()
        for relpath_f in seq_in:
            abspath_src = resolve_joinpath(path_cwd, relpath_f)
            abspath_dest = resolve_joinpath(path_tmp_dir, relpath_f)
            shutil.copy2(abspath_src, abspath_dest)

        #    Needed by '.venv'
        seq_in_supplemental = [
            "requirements/pip.in",
            "requirements/pip-tools.in",
            "requirements/dev.in",
            "requirements/manage.in",
            "docs/pip-tools.in",
            "requirements/pins.shared.in",
            "requirements/pins-typing.in",
        ]
        prepare_folders_files(seq_in_supplemental, path_tmp_dir)
        for relpath_f in seq_in_supplemental:
            abspath_src = resolve_joinpath(path_cwd, relpath_f)
            abspath_dest = resolve_joinpath(path_tmp_dir, relpath_f)
            shutil.copy2(abspath_src, abspath_dest)

        # Limit to one venv relpath, rather than run all
        is_lock_compile = fcn.callback.__name__ == "requirements_fix_v2"
        result = runner.invoke(fcn, cmd)
        actual_exit_code = result.exit_code
        # Contains venv_relpath, lock file, err, exception
        actual_output = result.output  # noqa: F841
        actual_exception = result.exception  # noqa: F841
        if not is_lock_compile:
            assert actual_exit_code == expected_exit_code
        else:
            # Is lock_compile
            is_not_timeout = actual_exit_code != 10
            if is_not_timeout:
                assert actual_exit_code == expected_exit_code
                if actual_exit_code == 0:
                    # Fake a timeout
                    with patch(
                        f"{g_app_name}.cli_dependencies.is_timeout",
                        return_value=True,
                    ):
                        result = runner.invoke(fcn, cmd)
                        actual_exit_code = result.exit_code
                        assert actual_exit_code == 10
            else:
                # Timeout occurred, do not have to fake one
                pass


testdata_lock_unlock_and_back_wo_prepare = (
    (
        requirements_unlock,
        Path(__file__).parent.joinpath("_good_files", "complete.pyproject_toml"),
        ".venv/docs",
        3,  # FileNotFoundError
    ),
    (
        requirements_fix_v2,
        Path(__file__).parent.joinpath("_good_files", "complete.pyproject_toml"),
        ".venv/docs",
        3,  # FileNotFoundError
    ),
)
ids_lock_unlock_and_back_wo_prepare = (
    "call requirements_unlock. Additional file ci/kit.in",
    "call requirements_fix_v2. Additional file ci/kit.in",
)


@pytest.mark.logging_package_name(g_app_name)
@pytest.mark.parametrize(
    "func, path_pyproject_toml, venv_path, expected_exit_code",
    testdata_lock_unlock_and_back_wo_prepare,
    ids=ids_lock_unlock_and_back_wo_prepare,
)
def test_lock_unlock_and_back_wo_prepare(
    func,
    path_pyproject_toml,
    venv_path,
    expected_exit_code,
    tmp_path,
    prep_pyproject_toml,
    logging_strict,
):
    """Test dependency lock and unlock without prepare."""
    # pytest --showlocals --log-level INFO -k "test_lock_unlock_and_back_wo_prepare" -v tests
    t_two = logging_strict()
    logger, loggers = t_two

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as tmp_dir_path:
        path_tmp_dir = Path(tmp_dir_path)

        # w/o prepare pyproject.toml
        cmd = (
            "--path",
            path_tmp_dir,
            "--venv-relpath",
            venv_path,
        )
        result = runner.invoke(func, cmd)

        logger.info(result.output)
        tb = result.exc_info[2]
        # msg_info = f"traceback: {pprint(traceback.format_tb(tb))}"
        msg_info = f"traceback: {traceback.format_tb(tb)}"
        logger.info(msg_info)

        actual_exit_code = result.exit_code
        assert actual_exit_code == expected_exit_code


testdata_lock_unlock_compile_with_prepare = (
    (
        requirements_fix_v2,
        Path(__file__).parent.joinpath("_good_files", "complete.pyproject_toml"),
        ".doc/.venv",
        True,
        False,
        6,  # 6 MissingRequirementsFoldersFiles
    ),
    (
        requirements_unlock,
        Path(__file__).parent.joinpath("_good_files", "complete.pyproject_toml"),
        ".doc/.venv",
        True,
        False,
        6,  # 6 MissingRequirementsFoldersFiles
    ),
    pytest.param(
        requirements_fix_v2,
        Path(__file__).parent.joinpath("_good_files", "complete.pyproject_toml"),
        ".venv/docs",
        True,
        True,
        9,
    ),
    (
        requirements_unlock,
        Path(__file__).parent.joinpath("_good_files", "complete.pyproject_toml"),
        ".venv/docs",
        True,
        True,
        9,
    ),
)
ids_lock_unlock_compile_with_prepare = (
    "lock missing folders and files",
    "unlock missing folders and files",
    "lock nonexistent venv path",
    "unlock nonexistent venv path",
)


@pytest.mark.logging_package_name(g_app_name)
@pytest.mark.parametrize(
    "func, path_pyproject_toml, venv_path, is_prep_pyproject_toml, is_prep_files, expected_exit_code",
    testdata_lock_unlock_compile_with_prepare,
    ids=ids_lock_unlock_compile_with_prepare,
)
def test_lock_unlock_compile_with_prepare(
    func,
    path_pyproject_toml,
    venv_path,
    is_prep_pyproject_toml,
    is_prep_files,
    expected_exit_code,
    tmp_path,
    prep_pyproject_toml,
    path_project_base,
    prepare_folders_files,
    logging_strict,
):
    """Test dependency lock and unlock with prepare."""
    # pytest -v --showlocals --log-level INFO -k "test_lock_unlock_compile_with_prepare" tests
    t_two = logging_strict()
    logger, loggers = t_two

    path_cwd = path_project_base()

    # Must copy otherwise path_tmp_dir will not be able to find missing reqs
    seq_reqs_relpath = (
        "requirements/pins.shared.in",
        "requirements/prod.in",
        "docs/pip-tools.in",
        "docs/requirements.in",
        "requirements/pip.in",
        "requirements/pip-tools.in",
        "requirements/dev.in",
        "requirements/manage.in",
        "requirements/pins-cffi.in",
        "requirements/tox.in",
    )

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as tmp_dir_path:
        path_tmp_dir = Path(tmp_dir_path)
        # prepare -- pyproject.toml
        if is_prep_pyproject_toml:
            prep_pyproject_toml(path_pyproject_toml, path_tmp_dir)

        # prepare -- venv folder(s)
        venv_relpaths = (
            ".venv",
            ".doc/.venv",
        )
        for create_relpath in venv_relpaths:
            abspath_venv = resolve_joinpath(path_tmp_dir, create_relpath)
            abspath_venv.mkdir(parents=True, exist_ok=True)

        if is_prep_files:
            prepare_folders_files(seq_reqs_relpath, path_tmp_dir)
            for relpath_f in seq_reqs_relpath:
                abspath_src = resolve_joinpath(path_cwd, relpath_f)
                abspath_dest = resolve_joinpath(path_tmp_dir, relpath_f)
                shutil.copy2(abspath_src, abspath_dest)

        cmd = (
            "--path",
            path_tmp_dir,
            "--venv-relpath",
            venv_path,
        )
        # Call cli func blind; no BackendType.is_locked
        result = runner.invoke(func, cmd)

        logger.info(f"exit_code: {result.exit_code}")
        logger.info(f"exception: {result.exception}")
        logger.info(f"output: {result.output}")

        tb = result.exc_info[2]
        # msg_info = f"traceback: {pprint(traceback.format_tb(tb))}"
        msg_info = f"traceback: {traceback.format_tb(tb)}"
        logger.info(msg_info)

        actual_exit_code = result.exit_code
        assert actual_exit_code == expected_exit_code


testdata_lock_compile_requires_pip_tools = (
    (
        requirements_fix_v2,
        Path(__file__).parent.joinpath("_req_files", "venvs_minimal.pyproject_toml"),
        ".tools",
        (
            "docs/pip-tools",
            "requirements/pins.shared",
            "requirements/pip-tools",
            "requirements/pip",
        ),
        5,
    ),
    (
        requirements_fix_v2,
        Path(__file__).parent.joinpath("_req_files", "venvs_minimal.pyproject_toml"),
        ".awesome",
        (
            "docs/pip-tools",
            "requirements/pins.shared",
            "requirements/pip-tools",
            "requirements/pip",
        ),
        9,
    ),
)
ids_lock_compile_requires_pip_tools = (
    "pip-tools is not installed",
    "no such venv key",
)


@pytest.mark.logging_package_name(g_app_name)
@pytest.mark.parametrize(
    "fcn, path_pyproject_toml, venv_path, seqs_reqs, expected_exit_code",
    testdata_lock_compile_requires_pip_tools,
    ids=ids_lock_compile_requires_pip_tools,
)
def test_lock_compile_requires_pip_tools(
    fcn,
    path_pyproject_toml,
    venv_path,
    seqs_reqs,
    expected_exit_code,
    tmp_path,
    prep_pyproject_toml,
    path_project_base,
    logging_strict,
):
    """Test lock_compile install pip-tools 5"""
    # pytest -vv --showlocals --log-level INFO -k "test_lock_compile_requires_pip_tools" tests
    t_two = logging_strict()
    logger, loggers = t_two

    path_cwd = path_project_base()

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as tmp_dir_path:
        path_tmp_dir = Path(tmp_dir_path)
        cmd = (
            "--path",
            path_tmp_dir,
            "--venv-relpath",
            venv_path,
        )

        # prepare
        #    Copy to base dir
        prep_pyproject_toml(path_pyproject_toml, path_tmp_dir)

        # copy reqs
        for src_relpath in seqs_reqs:
            abspath_src = cast("Path", resolve_joinpath(path_cwd, src_relpath))
            abspath_src_in = replace_suffixes_last(abspath_src, SUFFIX_IN)
            src_in_abspath = str(abspath_src_in)
            abspath_dest = cast("Path", resolve_joinpath(path_tmp_dir, src_relpath))
            abspath_dest_in = replace_suffixes_last(abspath_dest, SUFFIX_IN)
            abspath_dest_in.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src_in_abspath, abspath_dest_in)

        #    create all venv folders. If missing --> 7
        venv_dirs = (".venv/docs", ".awesome", ".tools")
        for venv_dir in venv_dirs:
            path_dir = cast("Path", resolve_joinpath(path_tmp_dir, venv_dir))
            path_dir.mkdir(parents=True, exist_ok=True)

        if expected_exit_code == 5:
            with patch(
                f"{g_app_name}.lock_compile.is_package_installed",
                return_value=False,
            ):
                result = runner.invoke(fcn, cmd)
                logger.info(f"output: {result.output}")
                assert result.exit_code == expected_exit_code
        else:
            result = runner.invoke(fcn, cmd, catch_exceptions=True)

            logger.info(f"exception: {result.exception}")
            logger.info(f"output: {result.output}")

            tb = result.exc_info[2]
            # msg_info = f"traceback: {pprint(traceback.format_tb(tb))}"
            msg_info = f"traceback: {traceback.format_tb(tb)}"
            logger.info(msg_info)

            assert result.exit_code == expected_exit_code


testdata_lock_compile_valueerror = (
    (
        requirements_fix_v2,
        Path(__file__).parent.joinpath(
            "_bad_files",
            "keys-wrong-data-type.pyproject_toml",
        ),
        ".venv",
        (
            "docs/pip-tools",
            "requirements/pins.shared",
        ),
        ["-v"],
        8,
    ),
    (
        requirements_fix_v2,
        Path(__file__).parent.joinpath(
            "_bad_files",
            "keys-wrong-data-type.pyproject_toml",
        ),
        ".venv",
        (
            "docs/pip-tools",
            "requirements/pins.shared",
        ),
        [],
        8,
    ),
    (
        requirements_unlock,
        Path(__file__).parent.joinpath(
            "_bad_files",
            "keys-wrong-data-type.pyproject_toml",
        ),
        ".venv",
        (
            "docs/pip-tools",
            "requirements/pins.shared",
        ),
        [],
        8,
    ),
    (
        requirements_fix_v2,
        Path(__file__).parent.joinpath(
            "_bad_files",
            "keys-wrong-data-type.pyproject_toml",
        ),
        None,
        (
            "docs/pip-tools",
            "requirements/pins.shared",
        ),
        [],
        12,
    ),
)
ids_lock_compile_valueerror = (
    "lock expecting tool.wreck.venvs.reqs to be a sequence verbose",
    "lock expecting tool.wreck.venvs.reqs to be a sequence not verbose",
    "unlock expecting tool.wreck.venvs.reqs to be a sequence",
    "venv_relpath not provided",
)


@pytest.mark.logging_package_name(g_app_name)
@pytest.mark.parametrize(
    "fcn, path_pyproject_toml, venv_path, seqs_reqs, extend_args, expected_exit_code",
    testdata_lock_compile_valueerror,
    ids=ids_lock_compile_valueerror,
)
def test_lock_compile_valueerror(
    fcn,
    path_pyproject_toml,
    venv_path,
    seqs_reqs,
    extend_args,
    expected_exit_code,
    tmp_path,
    prep_pyproject_toml,
    logging_strict,
):
    """Test lock_compile ValueError 8"""
    # pytest -vv --showlocals --log-level INFO -k "test_lock_compile_valueerror" tests
    t_two = logging_strict()
    logger, loggers = t_two

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as tmp_dir_path:
        path_tmp_dir = Path(tmp_dir_path)

        # prepare
        #    Copy to base dir
        prep_pyproject_toml(path_pyproject_toml, path_tmp_dir)

        #    Build cmd
        cmd = [
            "--path",
            path_tmp_dir,
        ]

        if venv_path is not None:
            cmd_venv = [
                "--venv-relpath",
                venv_path,
            ]
            cmd.extend(cmd_venv)

        cmd.extend(extend_args)

        # act
        result = runner.invoke(fcn, cmd, catch_exceptions=True)
        # verify
        assert result.exit_code == expected_exit_code
