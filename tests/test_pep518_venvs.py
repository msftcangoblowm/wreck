"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Without coverage

.. code-block:: shell

   pytest -vv --showlocals tests/test_pep518_venvs.py

With coverage

.. code-block:: shell

   python -m coverage run --source='wreck.pep518_venvs' -m pytest \
   --showlocals tests/test_pep518_venvs.py && coverage report \
   --data-file=.coverage --include="**/pep518_venvs.py"

"""

import shutil
from contextlib import nullcontext as does_not_raise
from pathlib import (
    Path,
    PurePath,
)
from typing import (
    TYPE_CHECKING,
    cast,
)

import pytest

from wreck._safe_path import resolve_joinpath
from wreck.constants import SUFFIX_IN
from wreck.exceptions import (
    MissingPackageBaseFolder,
    MissingRequirementsFoldersFiles,
)
from wreck.pep518_venvs import (
    VenvMap,
    VenvMapLoader,
    VenvReq,
    check_venv_relpath,
    get_reqs,
)

if TYPE_CHECKING:
    from collections.abc import (
        Callable,
        MutableSet,
        Sequence,
    )
    from typing import Union

    from tests.typing_only import DOES_NOT_OR_DOES


def test_venvmaploader(
    request: "pytest.FixtureRequest",
    tmp_path: "Path",
    prep_pyproject_toml: "Callable[[Path, Path, Union[Path, str, None]], Path]",
    prepare_folders_files: "Callable[[Union[Sequence[Union[str, Path]], MutableSet[Union[str, Path]]], Path], set[Path]]",
) -> None:
    """Test VenvMapLoader."""
    # pytest --showlocals --log-level INFO -k "test_venvmaploader" tests
    abspath_tests_dir = request.path.parent
    invalids_0 = (
        (3, "unsupported type. Within context, file not found"),
        (tmp_path, "No pyproject.toml or .pyproject_toml found"),
    )
    for t_invalid_0 in invalids_0:
        invalid_0, _ = t_invalid_0
        with pytest.raises(FileNotFoundError):
            VenvMapLoader(
                invalid_0,  # type: ignore[arg-type]
            )

    # Finds an empty file --> LookupError
    path_dest_pyproject_toml = tmp_path / "pyproject.toml"
    path_dest_pyproject_toml.touch()
    dest_pyproject_toml_path = path_dest_pyproject_toml.as_posix()
    with pytest.raises(LookupError):
        VenvMapLoader(dest_pyproject_toml_path)

    # Fail during parsing
    prep_these_1 = (
        ".venv/crap.txt",
        ".doc/.venv/crap.txt",
    )
    prepare_folders_files(prep_these_1, tmp_path)

    # no reqs files --> missing
    path_pyproject_toml = abspath_tests_dir.joinpath(
        "_req_files",
        "venvs.pyproject_toml",
    )
    path_dest_pyproject_toml = prep_pyproject_toml(path_pyproject_toml, tmp_path, None)
    loader = VenvMapLoader(path_dest_pyproject_toml.as_posix())
    data_before_parse = loader.l_data  # noqa: F841
    venv_reqs, lst_missing = loader.parse_data()
    assert len(lst_missing) != 0
    assert len(lst_missing) == len(venv_reqs)

    # Prepare some, not all
    base_relpaths_2 = (
        "requirements/pip-tools",
        "requirements/pip",
        "requirements/prod.shared",
        "requirements/kit",
    )
    prep_these_2 = []
    for suffix in (".in", ".unlock", ".lock"):
        for base_relpath in base_relpaths_2:
            prep_these_2.append(f"{base_relpath}{suffix}")
    prepare_folders_files(prep_these_2, tmp_path)
    loader = VenvMapLoader(path_dest_pyproject_toml.as_posix())
    venv_reqs, lst_missing = loader.parse_data(check_suffixes=None)
    assert len(lst_missing) != 0
    assert len(lst_missing) != len(venv_reqs)

    venv_map = VenvMap(loader)
    venv_map_missing_count = len(venv_map.missing)
    assert venv_map_missing_count != 0
    assert venv_map.project_base == tmp_path
    repr_venv_map = repr(venv_map)
    assert isinstance(repr_venv_map, str)
    assert len(venv_map) != 0
    # iterate over map
    for venvreq in venv_map:
        pass
    # __contains__
    venv_relpath = ".venv"
    assert venv_relpath in venv_map
    is_nonsense_in_venv_map = 3 in venv_map
    assert is_nonsense_in_venv_map is False

    # __getitem__
    venv_map[0:1]
    venv_map[1]
    with pytest.raises(TypeError):
        venv_map["1"]  # type: ignore[index]
    venv_map[-1]
    with pytest.raises(IndexError):
        venv_map[20000]

    with pytest.raises(KeyError):
        venv_map.reqs("nonexistent-file.in")

    # ensure_abspath unsupported type. Expects str or Path
    with pytest.raises(TypeError):
        loader.ensure_abspath(5)  # type: ignore[arg-type]

    # ensure_abspath with abspath
    path_actual = loader.ensure_abspath(path_dest_pyproject_toml)
    assert path_actual == path_dest_pyproject_toml

    base_relpaths_3 = (
        "requirements/pip-tools",
        "requirements/pip",
        "requirements/prod.shared",
        "requirements/kit",
        "requirements/tox",
        "requirements/mypy",
        "requirements/manage",
        "requirements/dev",
    )
    prep_these_3 = []
    for suffix in (".in", ".unlock", ".lock"):
        for base_relpath in base_relpaths_3:
            prep_these_3.append(f"{base_relpath}{suffix}")
    prepare_folders_files(prep_these_3, tmp_path)

    venvreqs = venv_map.reqs(venv_relpath)
    assert isinstance(venvreqs, list)
    assert len(venvreqs) == len(base_relpaths_3)

    path_pyproject_toml = abspath_tests_dir.joinpath(
        "_req_files",
        "venvs-not-folder.pyproject_toml",
    )
    path_dest_pyproject_toml = prep_pyproject_toml(path_pyproject_toml, tmp_path, None)

    loader = VenvMapLoader(path_dest_pyproject_toml.as_posix())
    with pytest.raises(NotADirectoryError):
        loader.parse_data()

    path_pyproject_toml = abspath_tests_dir.joinpath(
        "_req_files",
        "venvs-reqs-not-sequence.pyproject_toml",
    )
    path_dest_pyproject_toml = prep_pyproject_toml(path_pyproject_toml, tmp_path, None)
    loader = VenvMapLoader(path_dest_pyproject_toml.as_posix())
    with pytest.raises(ValueError):
        loader.parse_data()


testdata_venvreq = (
    (
        ".venv",
        "requirements/dev",
        ("requirements",),
        does_not_raise(),
    ),
    (
        ".venv/crap.txt",
        "requirements/dev",
        ("requirements",),
        does_not_raise(),
    ),
)
ids_venvreq = (
    "in .venv, a dev requirement",
    "will raise NotADirectoryError during parsing, not during load",
)


@pytest.mark.parametrize(
    "venv_relpath, req_relpath, t_folders_relpath, expectation",
    testdata_venvreq,
    ids=ids_venvreq,
)
def test_venvreq(
    venv_relpath: str,
    req_relpath: str,
    t_folders_relpath: "tuple[str, ...]",
    expectation: "DOES_NOT_OR_DOES",
    tmp_path: "Path",
    prepare_folders_files: "Callable[[Union[Sequence[Union[str, Path]], MutableSet[Union[str, Path]]], Path], set[Path]]",
) -> None:
    """Test VenvReq."""
    # pytest --showlocals --log-level INFO -k "test_venvreq" tests
    # prepare
    #    venv folder
    prepare_folders_files((venv_relpath,), tmp_path)
    venv_relpath_tmp = venv_relpath
    abspath_venv = cast("Path", resolve_joinpath(tmp_path, venv_relpath))
    if not abspath_venv.exists():
        venv_relpath_tmp += "/.python_version"
        prepare_folders_files((venv_relpath_tmp,), tmp_path)

    #    requirements
    seq_relpath = []
    suffix_types = (".in", ".unlock", ".lock")
    for suffix in suffix_types:
        seq_relpath.append(f"{req_relpath}{suffix}")
    prepare_folders_files(seq_relpath, tmp_path)

    with expectation:
        vr = VenvReq(tmp_path, venv_relpath, req_relpath, t_folders_relpath)
    if isinstance(expectation, does_not_raise):
        repr_vr = repr(vr)
        assert isinstance(repr_vr, str)

        # Is not shared between venvs. Those requirement files should have suffix, .shared
        assert not vr.is_req_shared

        assert vr.venv_abspath.relative_to(tmp_path) == Path(venv_relpath)
        assert vr.req_abspath.relative_to(tmp_path) == Path(f"{req_relpath}.in")

        abspath_in_files = list(vr.reqs_all(".in"))
        assert len(abspath_in_files) == len(seq_relpath) / len(suffix_types)


testdata_venv_get_reqs = (
    (
        Path("_req_files").joinpath("venvs.pyproject_toml"),
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
    ),
    (
        Path("_req_files").joinpath("venvs.pyproject_toml"),
        ".doc/.venv",
        (
            (
                Path(__file__).parent.parent.joinpath(
                    "docs",
                    "pip-tools.in",
                ),
                "docs/pip-tools.in",
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
            "docs/pip-tools",
            "docs/requirements",
        ),
        does_not_raise(),
        2,
    ),
    (
        Path("_requirements_none").joinpath("requires-none.pyproject_toml"),
        ".venv",
        (),
        (),
        does_not_raise(),
        0,
    ),
    (
        Path("_requirements_none").joinpath("requires-none.pyproject_toml"),
        0.1234,
        (),
        (),
        pytest.raises(TypeError),
        0,
    ),
    (
        Path("_req_files").joinpath("venvs.pyproject_toml"),
        ".doc/.venv",
        (
            (
                Path(__file__).parent.parent.joinpath(
                    "docs",
                    "pip-tools.in",
                ),
                "docs/pip-tools.in",
            ),
        ),
        ("docs/pip-tools",),
        pytest.raises(MissingRequirementsFoldersFiles),
        2,
    ),
)
ids_venv_get_reqs = (
    "venvs.pyproject_toml .venv",
    "venvs.pyproject_toml .doc/.venv",
    "tool.wreck.venvs section no requirements",
    "venv_path unsupported type expected str",
    "missing top level docs/requirement requirement file",
)


@pytest.mark.parametrize(
    (
        "relpath_pyproject_toml, venv_relpath, seq_reqs, base_relpaths, "
        "expectation, expected_req_file_count"
    ),
    testdata_venv_get_reqs,
    ids=ids_venv_get_reqs,
)
def test_venv_get_reqs(
    relpath_pyproject_toml: "Path",
    venv_relpath: str,
    seq_reqs: "Sequence[tuple[Path, str]]",
    base_relpaths: "Sequence[str]",
    expectation: "DOES_NOT_OR_DOES",
    expected_req_file_count: int,
    request: "pytest.FixtureRequest",
    tmp_path: "Path",
    prep_pyproject_toml: "Callable[[Path, Path, Union[Path, str, None]], Path]",
    prepare_folders_files: "Callable[[Union[Sequence[Union[str, Path]], MutableSet[Union[str, Path]]], Path], set[Path]]",
) -> None:
    """Test get_reqs"""
    # pytest --showlocals --log-level INFO -k "test_venv_get_reqs" tests
    # pytest --showlocals --log-level INFO tests/test_pep518_venvs.py::test_venv_get_reqs[tool.wreck.venvs\ section\ no\ requirements]
    abspath_tests_dir = request.path.parent
    path_pyproject_toml = abspath_tests_dir.joinpath(relpath_pyproject_toml)
    # prepare
    #    pyproject.toml
    path_dest_pyproject_toml = prep_pyproject_toml(path_pyproject_toml, tmp_path, None)

    #    empty folders
    seq_folders = (
        ".venv/.python-version",
        ".doc/.venv/.python-version",
        "docs/empty.txt",
        "requirements/empty.txt",
    )
    prepare_folders_files(seq_folders, tmp_path)
    loader = VenvMapLoader(path_dest_pyproject_toml.as_posix())

    # loader invalid --> MissingPackageBaseFolder
    with pytest.raises(MissingPackageBaseFolder):
        get_reqs(
            None,  # type: ignore[arg-type]
            venv_path=venv_relpath,
            suffix_last=SUFFIX_IN,
        )

    #    requirements empty files and folders
    suffixes = (SUFFIX_IN,)
    seq_rel_paths = []
    for base_relpath in base_relpaths:
        for suffix in suffixes:
            seq_rel_paths.append(f"{base_relpath}{suffix}")
    prepare_folders_files(seq_rel_paths, tmp_path)

    #    overwrite some req relpath src --> dest e.g. 'requirements/dev.unlock'
    for t_paths in seq_reqs:
        src_abspath, dest_relpath = t_paths

        # If a .shared requirement file, get abspath
        vr = VenvReq(
            loader.project_base,
            venv_relpath,
            dest_relpath,
            ("docs", "requirements"),
        )
        if vr.is_req_shared:
            vr.req_abspath

        abspath_dest = cast("Path", resolve_joinpath(tmp_path, dest_relpath))
        shutil.copy(src_abspath, abspath_dest)

    # No such venv
    with pytest.raises(KeyError):
        get_reqs(loader, ".dogfood", suffix_last=SUFFIX_IN)

    # venv_relpath is relative path
    with expectation:
        abspath_reqs_a = get_reqs(loader, venv_relpath, suffix_last=None)
    if isinstance(expectation, does_not_raise):
        actual_req_file_count_a = len(abspath_reqs_a)
        assert actual_req_file_count_a == expected_req_file_count

    # venv_relpath is absolute path. Otherwise continue
    if isinstance(venv_relpath, str) or issubclass(type(venv_relpath), PurePath):
        abspath_venv_b = cast("Path", resolve_joinpath(tmp_path, venv_relpath))
        with expectation:
            abspath_reqs_b = get_reqs(loader, abspath_venv_b, suffix_last=SUFFIX_IN)
        if isinstance(expectation, does_not_raise):
            actual_req_file_count_b = len(abspath_reqs_b)
            assert actual_req_file_count_b == expected_req_file_count

    # Call VenvMap.reqs, bypassing get_reqs multitude of checks and Exceptions
    ignore_excs = (MissingRequirementsFoldersFiles,)
    if isinstance(expectation, does_not_raise) or (
        not isinstance(expectation, does_not_raise)
        and expectation.expected_exception not in ignore_excs
    ):
        with expectation:
            venvs = VenvMap(
                loader,
                parse_venv_relpath=venv_relpath,
                check_suffixes=suffixes,
            )
            reqs = venvs.reqs(venv_relpath)
            if isinstance(expectation, does_not_raise):
                actual_req_file_count_c = len(reqs)
                assert actual_req_file_count_c == expected_req_file_count
            else:
                # skipped which Exception?
                expectation_exc = expectation.expected_exception  # noqa: F841


testdata_check_venv_relpath = (
    (
        Path("_req_files").joinpath("venvs.pyproject_toml"),
        0,
        Path("pyproject.toml"),
    ),
    (
        Path("_req_files").joinpath("venvs.pyproject_toml"),
        1,
        Path("pyproject.toml"),
    ),
    (
        Path("_req_files").joinpath("venvs.pyproject_toml"),
        "pyproject.toml",
        Path("pyproject.toml"),
    ),
    (
        Path("_req_files").joinpath("venvs.pyproject_toml"),
        Path("pyproject.toml"),
        Path("pyproject.toml"),
    ),
)
ids_check_venv_relpath = (
    "abspath Path",
    "abspath str",
    "relpath str",
    "relpath Path",
)


@pytest.mark.parametrize(
    "relpath_pyproject_toml, optpath_dest_config, expected",
    testdata_check_venv_relpath,
    ids=ids_check_venv_relpath,
)
def test_check_venv_relpath(
    relpath_pyproject_toml: "Path",
    optpath_dest_config: "Union[Path, str, int]",
    expected: "Path",
    request: "pytest.FixtureRequest",
    tmp_path: "Path",
    prep_pyproject_toml: "Callable[[Path, Path, Union[Path, str, None]], Path]",
) -> None:
    """Test check_venv_relpath"""
    # pytest -vv --showlocals --log-level INFO -k "test_check_venv_relpath" tests
    if TYPE_CHECKING:
        path_mixed: Union[Path, str]

    abspath_tests_dir = request.path.parent

    relpath_pyproject_toml = Path("_req_files").joinpath("venvs.pyproject_toml")
    path_pyproject_toml = abspath_tests_dir.joinpath(relpath_pyproject_toml)

    # prepare
    #    pyproject.toml or [something].pyproject_toml
    path_dest_config = prep_pyproject_toml(path_pyproject_toml, tmp_path, None)
    if optpath_dest_config == 0:
        path_mixed = path_dest_config
    elif optpath_dest_config == 1:
        path_mixed = path_dest_config.as_posix()
    else:
        path_mixed = cast("Union[Path, str]", optpath_dest_config)

    #    Careful path must be a str
    loader = VenvMapLoader(path_dest_config.as_posix())

    path_base_dir = loader.project_base
    #    Confirms pyproject.toml exists within tmp_path
    assert path_base_dir == tmp_path

    # act
    relpath_actual = check_venv_relpath(loader, path_mixed)
    # verify
    assert issubclass(type(relpath_actual), PurePath)
    assert relpath_actual == expected
