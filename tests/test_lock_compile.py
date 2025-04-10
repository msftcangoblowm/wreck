"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Unit test -- Module

.. code-block:: shell

   python -m coverage run --source='wreck.lock_compile' -m pytest \
   --showlocals tests/test_lock_compile.py && coverage report \
   --data-file=.coverage --include="**/lock_compile.py"

"""

import os
import shutil
from collections.abc import Generator
from contextlib import nullcontext as does_not_raise
from pathlib import (
    Path,
    PurePath,
)
from typing import cast

import pytest

from wreck._package_installed import is_package_installed
from wreck._run_cmd import run_cmd
from wreck._safe_path import (
    resolve_joinpath,
    resolve_path,
)
from wreck.constants import g_app_name
from wreck.exceptions import MissingRequirementsFoldersFiles
from wreck.lock_compile import (
    _compile_one,
    _empty_in_empty_out,
    _postprocess_abspath_to_relpath,
    is_timeout,
    lock_compile,
    prepare_pairs,
)
from wreck.pep518_venvs import (
    VenvMapLoader,
    get_reqs,
)

testdata_pipcompile_creates_1byte = (
    (
        (Path(__file__).parent.joinpath("_python_1byte", "empty.in"),),
        "requirements/empty.in",
        "requirements/empty.lock",
    ),
)
ids_pipcompile_creates_1byte = ("0B .in file 1B .lock file",)


@pytest.mark.xfail(
    not is_package_installed("pip-tools"),
    reason="dependency package pip-tools is required",
)
@pytest.mark.parametrize(
    "seq_copy_these, in_relpath, out_relpath",
    testdata_pipcompile_creates_1byte,
    ids=ids_pipcompile_creates_1byte,
)
def test_pipcompile_creates_1byte(
    seq_copy_these,
    in_relpath,
    out_relpath,
    tmp_path,
):
    """Prove pip-compile creates 1B file, from 0B .in

    If ``~/.pip/pip.conf`` has ``extra-index-url`` or ``index-url``
    will bleed into .lock file. Which throws off the output file size
    in bytes.

    Without ~/.pip/pip.conf interfering, ``pip-compile`` produces
    output file

    - expected: 0B

    - actual:   1B

    The 1B is a single posix line separator

    pip-compile puts ``--extra-index-url`` or ``--index-url`` flag
    lines into lock files. Those are environment specific and should be
    passed in on the cli

    Example installing package ``decimals`` available from local pypiserver

    .. code-block:: shell

       python -m pip install --extra-index-url="http://localhost:8081/simple/" decimals

    """
    # pytest -vv --showlocals --log-level INFO -k "test_pipcompile_creates_1byte" tests
    # prepare
    #    dest folders
    path_dir = cast("Path", resolve_joinpath(tmp_path, "requirements"))
    path_dir.mkdir(parents=True, exist_ok=True)

    #    copy seq_copy_these
    for abspath_src in seq_copy_these:
        src_abspath = str(abspath_src)
        abspath_dest = tmp_path / "requirements" / abspath_src.name
        shutil.copy2(src_abspath, abspath_dest)
    abspath_in = cast("Path", resolve_joinpath(tmp_path, in_relpath))
    abspath_out = cast("Path", resolve_joinpath(tmp_path, out_relpath))
    in_abspath = str(abspath_in)
    out_abspath = str(abspath_out)

    # act
    #    prove pip-compile creates 1B file, from 0B .in
    #    initial conditions
    assert abspath_in.stat().st_size == 0
    abspath_out.unlink(missing_ok=True)

    #   --no-header needed
    #   pip-compile stderr warning not written to file
    path_ep = resolve_path("pip-compile")
    cmd = (
        str(path_ep),
        "--no-header",
        "-o",
        out_abspath,
        in_abspath,
    )
    t_out = run_cmd(cmd, cwd=tmp_path)
    stdout, stderr, int_exit_code, exc = t_out
    assert int_exit_code == 0
    assert exc is None
    #    pip-compile writes a cryptic unactionable warning
    assert stderr is not None
    #    whitespace or empty
    assert stdout is None

    str_contents = abspath_out.read_text()
    sep = os.linesep
    lines = str_contents.split(sep)
    lines_minus_flags = [
        line
        for line in lines
        if not line.startswith("--extra-index-url")
        and not line.startswith("--index-url")
        and len(line) != 0
        and line != "\n"
    ]
    line_count = len(lines_minus_flags)

    assert line_count == 0


testdata_empty_in_empty_out = (
    (
        (Path(__file__).parent.joinpath("_python_1byte", "empty.in"),),
        "requirements/empty.in",
        "requirements/empty.lock",
        True,
        "",
    ),
    (
        (
            Path(__file__).parent.joinpath("_python_1byte", "empty.in"),
            Path(__file__).parent.joinpath("_python_1byte", "empty.lock"),
        ),
        "requirements/empty.in",
        "requirements/empty.lock",
        True,
        "",
    ),
)
ids_empty_in_empty_out = (
    "0B in file created using touch. No pre-existing lock file",
    "0B in file created using touch. Pre-existing lock file",
)


@pytest.mark.xfail(
    not is_package_installed("pip-tools"),
    reason="dependency package pip-tools is required",
)
@pytest.mark.parametrize(
    "seq_copy_these, in_relpath, out_relpath, is_in_empty_expected, expected_out",
    testdata_empty_in_empty_out,
    ids=ids_empty_in_empty_out,
)
def test_empty_in_empty_out(
    seq_copy_these,
    in_relpath,
    out_relpath,
    is_in_empty_expected,
    expected_out,
    tmp_path,
    prepare_folders_files,
):
    """If .in is empty file pip-compile creates 1B file. Create 0B instead"""
    # pytest -vv --showlocals --log-level INFO -k "test_empty_in_empty_out" tests
    # prepare
    #    dest folders
    path_dir = cast("Path", resolve_joinpath(tmp_path, "requirements"))
    path_dir.mkdir(parents=True, exist_ok=True)

    #    copy seq_copy_these
    for abspath_src in seq_copy_these:
        src_abspath = str(abspath_src)
        abspath_dest = tmp_path / "requirements" / abspath_src.name
        shutil.copy2(src_abspath, abspath_dest)
    abspath_in = cast("Path", resolve_joinpath(tmp_path, in_relpath))
    abspath_out = cast("Path", resolve_joinpath(tmp_path, out_relpath))
    in_abspath = abspath_in.as_posix()
    out_abspath = abspath_out.as_posix()

    #    Before _empty_in_empty_out .lock may not exist
    if abspath_out.exists():
        abspath_out_size_before = abspath_out.stat().st_size  # noqa: F841

    is_in_empty_actual = _empty_in_empty_out(in_abspath, out_abspath)
    assert is_in_empty_actual == is_in_empty_expected

    assert abspath_out.exists()

    #    compare file contents
    actual_out = abspath_out.read_text()
    assert actual_out == expected_out

    # bypassing pip-compile so .lock is 0Bytes
    # empty file size may differ by OS (Windows, MacOS == 1 ??)
    abspath_out_size_after = abspath_out.stat().st_size
    assert abspath_out_size_after == 0


testdata_compile_one = (
    (
        (
            Path(__file__).parent.parent.joinpath("requirements/pins.shared.in"),
            Path(__file__).parent.parent.joinpath("requirements/pip.in"),
            Path(__file__).parent.parent.joinpath("requirements/pip-tools.in"),
        ),
        "requirements/pip-tools.in",
        "requirements/pip-tools.out",
        None,
    ),
    (
        (
            Path(__file__).parent.joinpath("_python_1byte/empty.in"),
            Path(__file__).parent.joinpath("_python_1byte/empty.lock"),  # 1 Byte not 0B
        ),
        "requirements/empty.in",
        "requirements/empty.out",
        1,  # len(os.linesep) is 2 on Windows
    ),
)
ids_compile_one = (
    "pip-tools.in --> pip-tools.lock pip-compile upgrades dependencies",
    "empty.in --> empty.lock 1B file containing newline. Skips pip-compile",
)


@pytest.mark.xfail(
    not is_package_installed("pip-tools"),
    reason="dependency package pip-tools is required",
)
@pytest.mark.parametrize(
    "seq_copy_these, in_relpath, out_relpath, expected_file_size_bytes",
    testdata_compile_one,
    ids=ids_compile_one,
)
def test_compile_one_normal(
    seq_copy_these,
    in_relpath,
    out_relpath,
    expected_file_size_bytes,
    tmp_path,
):
    """Use pip-compile to compile lock an .in file. No bypass for empty .in file"""
    # pytest -vv --showlocals --log-level INFO -k "test_compile_one_normal" tests
    path_ep = resolve_path("pip-compile")
    ep_path = str(path_ep)
    path_cwd = tmp_path
    context = ".venv"

    # prepare
    #    dest folders
    path_dir = cast("Path", resolve_joinpath(tmp_path, "requirements"))
    path_dir.mkdir(parents=True, exist_ok=True)

    #    Copy real .in files
    for abspath_src in seq_copy_these:
        src_abspath = str(abspath_src)
        abspath_dest = tmp_path / "requirements" / abspath_src.name
        shutil.copy2(src_abspath, abspath_dest)
    abspath_in = cast("Path", resolve_joinpath(tmp_path, in_relpath))
    abspath_out = cast("Path", resolve_joinpath(tmp_path, out_relpath))
    in_abspath = abspath_in.as_posix()
    out_abspath = abspath_out.as_posix()

    # Conforms to interface?
    assert isinstance(in_abspath, str)
    assert isinstance(out_abspath, str)
    assert not Path(out_abspath).exists() and not Path(out_abspath).is_file()
    assert isinstance(ep_path, str)
    assert issubclass(type(path_cwd), PurePath)
    assert context is None or isinstance(context, str)

    # act
    optabspath_out, err_details = _compile_one(
        in_abspath,
        out_abspath,
        ep_path,
        path_cwd,
        context,
        timeout=PurePath,
    )
    # verify
    t_msg_failure = (context, Path(out_abspath), err_details)
    t_failures = (t_msg_failure,)
    if err_details is not None and is_timeout(t_failures):
        pytest.skip("lock_compile requires a web connection")
    else:
        assert optabspath_out is not None
        assert issubclass(type(optabspath_out), PurePath)
        assert optabspath_out.exists() and optabspath_out.is_file()
        # Expected .lock file size
        if expected_file_size_bytes is not None:
            #    To confirm file size
            #    stat -c %s testfile.txt
            # ~/.pip/pip.conf could add lines starting with extra-link
            str_contents = optabspath_out.read_text()
            sep = os.linesep
            lines = str_contents.split(sep)
            lines_minus_flags = [
                line
                for line in lines
                if not line.startswith("--extra-index-url")
                and not line.startswith("--index-url")
                and len(line) != 0
                and line != "\n"
            ]
            line_count = len(lines_minus_flags)
            assert line_count == 0


testdata_lock_file_paths_to_relpath = (
    (
        (
            "requirements/prod.shared.in",
            "docs/requirements.in",
        ),
        (
            "#\n"
            "click==8.1.7\n"
            "    # via\n"
            "    #   -c {tmp_path!s}/docs/../requirements/prod.shared.in\n"
            "    #   click-log\n"
            "    #   scriv\n"
            "    #   sphinx-external-toc-strict\n"
            "    #   uvicorn\n"
            "sphobjinv==2.3.1.1\n"
            "    # via -r {tmp_path!s}/docs/requirements.in\n\n"
        ),
        (
            "#\n"
            "click==8.1.7\n"
            "    # via\n"
            "    #   -c docs/../requirements/prod.shared.in\n"
            "    #   click-log\n"
            "    #   scriv\n"
            "    #   sphinx-external-toc-strict\n"
            "    #   uvicorn\n"
            "sphobjinv==2.3.1.1\n"
            "    # via -r docs/requirements.in\n\n"
        ),
        "docs/requirements.lock",
    ),
)
ids_lock_file_paths_to_relpath = ("remove absolute paths from .lock file",)


@pytest.mark.parametrize(
    "seq_reqs_relpath, lock_file_contents, expected_contents, dest_relpath",
    testdata_lock_file_paths_to_relpath,
    ids=ids_lock_file_paths_to_relpath,
)
def test_lock_file_paths_to_relpath(
    seq_reqs_relpath,
    lock_file_contents,
    expected_contents,
    dest_relpath,
    tmp_path,
    prepare_folders_files,
):
    """When creating .lock files post processor abs path --> relative path."""
    # pytest --showlocals --log-level INFO -k "test_lock_file_paths_to_relpath" tests
    # prepare
    #    .in
    prepare_folders_files(seq_reqs_relpath, tmp_path)

    #    .lock create with contents
    path_doc_lock = cast("Path", resolve_joinpath(tmp_path, dest_relpath))
    path_doc_lock.write_text(lock_file_contents.format(**{"tmp_path": tmp_path}))

    # act
    _postprocess_abspath_to_relpath(path_doc_lock, tmp_path)

    # verify
    #    Within file contents, absolute path of parent folder is absent
    actual_contents = path_doc_lock.read_text()
    is_not_occur_once = str(tmp_path) not in actual_contents
    assert is_not_occur_once is True
    assert actual_contents == expected_contents


testdata_lock_compile_live = (
    pytest.param(
        Path(__file__).parent.joinpath("_req_files", "venvs_minimal.pyproject_toml"),
        ".tools",
        (
            "requirements/pins.shared.in",
            "docs/pip-tools.in",
        ),
        "docs/pip-tools.in",
        "docs/pip-tools.out",
        does_not_raise(),
    ),
    pytest.param(
        Path(__file__).parent.joinpath("_req_files", "venvs_minimal.pyproject_toml"),
        ".venv",
        (
            "requirements/pins.shared.in",
            "requirements/pip.in",
            "requirements/pip-tools.in",
        ),
        "requirements/pip-tools.in",
        "requirements/pip-tools.out",
        does_not_raise(),
    ),
)
ids_lock_compile_live = (
    "recipe for docs/pip-tools.in --> docs/pip-tools.lock",
    "recipe for requirements/pip-tools.in --> requirements/pip-tools.lock",
)


@pytest.mark.logging_package_name(g_app_name)
@pytest.mark.xfail(
    not is_package_installed("pip-tools"),
    reason="dependency package pip-tools is required",
)
@pytest.mark.parametrize(
    "path_config, venv_relpath, seq_reqs_relpath, in_relpath, out_relpath, expectation",
    testdata_lock_compile_live,
    ids=ids_lock_compile_live,
)
def test_lock_compile_live(
    path_config,
    venv_relpath,
    seq_reqs_relpath,
    in_relpath,
    out_relpath,
    expectation,
    tmp_path,
    path_project_base,
    prep_pyproject_toml,
    prepare_folders_files,
    logging_strict,
):
    """Test lock_compile. Bypass applied for empty .in file, unlike _compile_one."""
    # pytest -vv --showlocals --log-level INFO -k "test_lock_compile_live" tests
    t_two = logging_strict()
    logger, loggers = t_two

    path_cwd = path_project_base()
    # prepare
    #    pyproject.toml
    path_f = prep_pyproject_toml(path_config, tmp_path)

    # Act
    #    Test without copying over support files
    loader = VenvMapLoader(path_f.as_posix())
    with pytest.raises(NotADirectoryError):
        lock_compile(loader, venv_relpath)
    #    Test not filtering by venv relpath
    with pytest.raises(NotADirectoryError):
        lock_compile(loader, None)

    #    create folders (venv and requirements folders)
    venv_relpaths = (
        ".venv",
        ".tools",
        "requirements",
        "docs",
    )
    for create_relpath in venv_relpaths:
        abspath_venv = cast("Path", resolve_joinpath(tmp_path, create_relpath))
        abspath_venv.mkdir(parents=True, exist_ok=True)

    #    Test without copying over support files
    loader = VenvMapLoader(path_f.as_posix())
    with pytest.raises(MissingRequirementsFoldersFiles):
        lock_compile(loader, venv_relpath)

    # prepare
    #    copy just the reqs .in
    abspath_src = cast("Path", resolve_joinpath(path_cwd, in_relpath))
    abspath_dest = cast("Path", resolve_joinpath(tmp_path, in_relpath))
    shutil.copy2(abspath_src, abspath_dest)

    # prepare
    #    copy (one venv, not all venv) requirements to respective folders
    for relpath_f in seq_reqs_relpath:
        abspath_src = cast("Path", resolve_joinpath(path_cwd, relpath_f))
        abspath_dest = cast("Path", resolve_joinpath(tmp_path, relpath_f))
        shutil.copy2(abspath_src, abspath_dest)

    # Act
    loader = VenvMapLoader(path_f.as_posix())

    # overloaded function prepare_pairs
    with expectation:
        # _, files = filter_by_venv_relpath(loader, venv_relpath)
        try:
            t_abspath_in = get_reqs(loader, venv_path=venv_relpath)
            # Generic -- To test prepare_pairs, must be InFiles
            # files = InFiles(path_cwd, t_abspath_in)
            # files.resolution_loop()
        except MissingRequirementsFoldersFiles:
            raise
        except (NotADirectoryError, ValueError, KeyError):
            raise

    if isinstance(expectation, does_not_raise):
        gen = prepare_pairs(t_abspath_in)
        assert isinstance(gen, Generator)
        list(gen)  # execute Generator

    with expectation:
        """
        from logging_strict.tech_niques import get_locals_dynamic
        args = (loader, venv_relpath)
        kwargs = {}
        t_ret = get_locals_dynamic(lock_compile, *args, **kwargs)  # noqa: F841
        t_status, t_locals = t_ret
        """
        t_status = lock_compile(
            loader,
            venv_relpath,
            timeout=PurePath,
        )
    # Verify
    if isinstance(expectation, does_not_raise):
        # assert has_logging_occurred(caplog)
        assert t_status is not None
        assert isinstance(t_status, tuple)
        t_compiled, t_failures = t_status
        assert isinstance(t_failures, tuple)
        assert isinstance(t_compiled, tuple)
        if is_timeout(t_failures):
            pytest.skip("lock_compile requires a web connection")
        else:
            is_no_failures = len(t_failures) == 0
            assert is_no_failures
            compiled_count = len(t_compiled)
            assert compiled_count == 1


testdata_compile_malformed_in = (
    (
        (Path(__file__).parent.joinpath("_malformed_in/malformed-pip.in"),),
        "requirements/malformed-pip.in",
        "requirements/malformed-pip.lock",
    ),
)
ids_compile_malformed_in = ("mix up order oper ver package",)


@pytest.mark.xfail(
    not is_package_installed("pip-tools"),
    reason="dependency package pip-tools is required",
)
@pytest.mark.parametrize(
    "seq_copy_these, in_relpath, out_relpath",
    testdata_compile_malformed_in,
    ids=ids_compile_malformed_in,
)
def test_compile_malformed_in(
    seq_copy_these,
    in_relpath,
    out_relpath,
    tmp_path,
):
    """Attempt to pip-compile a malformed .in file.

    .. seealso::

       Upstream bug

       `pip-tools#2139 <https://github.com/jazzband/pip-tools/issues/2139>`_

    """
    # pytest -vv --showlocals --log-level INFO -k "test_compile_malformed_in" tests
    path_ep = resolve_path("pip-compile")
    ep_path = str(path_ep)
    path_cwd = tmp_path
    context = ".venv"

    # prepare
    #    dest folders
    path_dir = cast("Path", resolve_joinpath(tmp_path, "requirements"))
    path_dir.mkdir(parents=True, exist_ok=True)
    path_venv = cast("Path", resolve_joinpath(tmp_path, ".venv"))
    path_venv.mkdir(parents=True, exist_ok=True)

    #    Copy real .in files
    for abspath_src in seq_copy_these:
        src_abspath = str(abspath_src)
        abspath_dest = tmp_path / "requirements" / abspath_src.name
        shutil.copy2(src_abspath, abspath_dest)
    abspath_in = cast("Path", resolve_joinpath(tmp_path, in_relpath))
    abspath_out = cast("Path", resolve_joinpath(tmp_path, out_relpath))
    in_abspath = abspath_in.as_posix()
    out_abspath = abspath_out.as_posix()

    # Conforms to interface?
    assert isinstance(in_abspath, str)
    assert isinstance(out_abspath, str)
    assert not Path(out_abspath).exists() and not Path(out_abspath).is_file()
    assert isinstance(ep_path, str)
    assert issubclass(type(path_cwd), PurePath)
    assert context is None or isinstance(context, str)

    # act
    optabspath_out, err_details = _compile_one(
        in_abspath,
        out_abspath,
        ep_path,
        path_cwd,
        context,
        timeout=PurePath,
    )
    # verify
    assert err_details is not None
    #    requirements parsing error occurs before web connection check.
    t_msg_failure = (context, Path(out_abspath), err_details)
    t_failures = (t_msg_failure,)

    is_no_web_connection = is_timeout(t_failures)
    # pytest.skip("lock_compile requires a web connection")
    assert is_no_web_connection is False

    # ugly traceback cuz pip-compile upstream bug
    assert optabspath_out is None
    assert "pip._internal.exceptions.InstallationError" in err_details


testdata_is_timeout = (
    (
        "blah blah blah timeout blah blah blah",
        True,
    ),
    (
        "blah blah blah blah blah blah",
        False,
    ),
)
ids_is_timeout = (
    "failure msg contains timeout",
    "failure msg does not contain timeout",
)


@pytest.mark.parametrize(
    "msg, timeout_expected",
    testdata_is_timeout,
    ids=ids_is_timeout,
)
def test_is_timeout(msg, timeout_expected):
    """Exercise is_timeout"""
    # pytest -vv --showlocals --log-level INFO -k "test_is_timeout" tests
    t_three = (None, None, msg)
    t_failure = (t_three,)
    timeout_actual = is_timeout(t_failure)
    assert timeout_actual is timeout_expected
