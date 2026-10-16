"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Without coverage

.. code-block:: shell

   python -m pytest -vv --showlocals tests/test_patch_pyproject_reading.py

With coverage

.. code-block:: shell

   python -m coverage run --source='wreck.monkey.patch_pyproject_reading' -m pytest \
   --showlocals tests/test_patch_pyproject_reading.py && coverage report \
   --data-file=.coverage --include="**/monkey/patch_pyproject_reading.py"

"""

import tomllib
from collections.abc import Sequence
from contextlib import nullcontext as does_not_raise
from pathlib import (
    Path,
    PurePath,
)
from typing import TYPE_CHECKING

import pytest

from wreck.constants import g_app_name
from wreck.monkey.patch_pyproject_reading import (
    PyProjectData,
    ReadPyproject,
    ReadPyprojectStrict,
)
from wreck.monkey.pyproject_reading import load_toml_or_inline_map

if TYPE_CHECKING:
    import logging
    from collections.abc import Callable
    from typing import (
        Any,
        Union,
    )

    from tests.typing_only import DOES_NOT_OR_DOES


@pytest.mark.parametrize(
    "tool_name, section, project, section_parent, expected_project_name",
    (
        pytest.param(
            "hope",
            {},
            {"name": "bob"},
            {},
            "bob",
            id="empty-section-pyproject.toml-contains-only-name",
        ),
        pytest.param(
            "hope.bob",
            {"citizenship": "usa", "occupation": "actor", "country-of-birth": "uk"},
            {"name": "famous"},
            {"parents-resident-state": "ohio"},
            "famous",
            id="dotted-section-with-parent-section",
        ),
    ),
)
def test_pyproject_data(
    tool_name: str,
    section: dict[str, str],
    project: dict[str, str],
    section_parent: dict[str, str],
    expected_project_name: str,
    tmp_path: "Path",
) -> None:
    """From pyproject.toml confirm can get project name."""
    # pytest --showlocals -vv --log-level INFO -k "test_pyproject_data" tests
    data = PyProjectData(tmp_path, tool_name, project, section, section_parent)
    actual_project_name = data.project_name
    assert actual_project_name == expected_project_name
    actual_section_parent = data.section_parent
    assert actual_section_parent == section_parent


@pytest.mark.parametrize(
    "tool_name, relpath_toml_file, expectation, expected_tool_name",
    (
        pytest.param(
            "drain-swamp",
            Path("_good_files").joinpath(
                "complete-manage-pip-prod-unlock.pyproject_toml"
            ),
            does_not_raise(),
            "drain-swamp",
            id="tool_name-str",
        ),
        pytest.param(
            ("drain-swamp",),
            Path("_good_files").joinpath(
                "complete-manage-pip-prod-unlock.pyproject_toml"
            ),
            does_not_raise(),
            "drain-swamp",
            id="tool_name-Sequence[str]",
        ),
        pytest.param(
            "drain-swamp",
            Path("_unsynced").joinpath("unsynced_1.lock"),
            pytest.raises(tomllib.TOMLDecodeError),
            "drain-swamp",
            id="not-a-toml-file",
        ),
        pytest.param(
            ("wreck.venvs", 7),
            Path("_duplicate_line").joinpath("prod_and_dev.pyproject_toml"),
            does_not_raise(),
            "wreck.venvs",
            id="unsupported-type-ignored",
        ),
        pytest.param(
            ("wreck.venvs", "   "),
            Path("_duplicate_line").joinpath("prod_and_dev.pyproject_toml"),
            does_not_raise(),
            "wreck.venvs",
            id="empty-str-or-whitespace-ignored",
        ),
        pytest.param(
            "wreck.venvs",
            Path("_duplicate_line").joinpath("prod_and_dev.pyproject_toml"),
            does_not_raise(),
            "wreck.venvs",
            id="tool-name-with-multiple-periods",
        ),
    ),
)
def test_read_pyproject_normal(
    tool_name: "Union[str, tuple[Any, ...]]",
    relpath_toml_file: "Path",
    expectation: "DOES_NOT_OR_DOES",
    expected_tool_name: str,
    request: "pytest.FixtureRequest",
    tmp_path: "Path",
    prep_pyproject_toml: "Callable[[Path, Path, Union[Path, str, None]], Path]",
) -> None:
    """Call ReadPyproject __call__. Pass in kwargs."""
    # pytest --showlocals -vv --log-level INFO -k "test_read_pyproject_normal" tests
    # pytest --showlocals -vv --log-level INFO tests/test_patch_pyproject_reading.py::test_read_pyproject_normal\[empty\ str\ or\ whitespace\ ignored\] tests
    abspath_tests_dir = request.path.parent
    path_pyproject_toml = abspath_tests_dir.joinpath(relpath_toml_file)

    # prepare
    prep_pyproject_toml(path_pyproject_toml, tmp_path, None)

    with expectation:
        data = ReadPyproject()(path=path_pyproject_toml, tool_name=tool_name)
    if isinstance(expectation, does_not_raise):
        assert issubclass(type(data.path), PurePath)
        assert isinstance(data.tool_name, str)
        assert isinstance(data.section, (dict, Sequence))
        assert isinstance(data.project, dict)
        assert data.path == path_pyproject_toml
        assert data.tool_name == expected_tool_name


@pytest.mark.parametrize(
    "tool_name, p_toml_file, expectation, in_keys_version_file, in_keys_copyright",
    (
        pytest.param(
            "Bob",
            Path("_good_files").joinpath("full-course-meal-and-shower.pyproject_toml"),
            pytest.raises(LookupError),
            False,
            False,
            id="Nonexistent-pyproject.toml",
        ),
        pytest.param(
            "Bob",
            Path("_good_files").joinpath(
                "complete-manage-pip-prod-unlock.pyproject_toml"
            ),
            pytest.raises(LookupError),
            False,
            True,
            id="No-such-section-[tool.Bob]",
        ),
        pytest.param(
            "drain-swamp",
            Path("_good_files").joinpath(
                "complete-manage-pip-prod-unlock.pyproject_toml"
            ),
            does_not_raise(),
            True,
            True,
            id="str",
        ),
        pytest.param(
            [
                "drain-swamp",
            ],
            Path("_good_files").joinpath(
                "complete-manage-pip-prod-unlock.pyproject_toml"
            ),
            does_not_raise(),
            True,
            True,
            id="Sequence[str]",
        ),
    ),
)
def test_read_pyproject_copyright_and_version(
    tool_name: "Union[str, Sequence[str]]",
    p_toml_file: "Path",
    expectation: "DOES_NOT_OR_DOES",
    in_keys_version_file: bool,
    in_keys_copyright: bool,
    request: "pytest.FixtureRequest",
) -> None:
    """ReadPyproject __call__ exceptions."""
    # pytest --showlocals -vv --log-level INFO -k "test_read_pyproject_copyright_and_version" tests
    abspath_tests_dir = request.path.parent
    path_pyproject_toml = abspath_tests_dir.joinpath(p_toml_file)

    with expectation:
        data_1 = ReadPyproject()(path=path_pyproject_toml, tool_name=tool_name)
    if isinstance(expectation, does_not_raise):
        assert isinstance(data_1.project, dict)
        assert isinstance(data_1.section, dict)
        assert data_1.project_name == "complete-awesome-perfect"
        keys = data_1.section.keys()
        #    from section drain-swamp
        assert in_keys_copyright == ("copyright_start_year" in keys)
        #    from section drain-swamp
        assert in_keys_version_file == ("version_file" in keys)


def test_update_dict_strict() -> None:
    """Update a ReadPyprojectStrict dict."""
    # pytest --showlocals -vv --log-level INFO -k "test_update_dict_strict" tests
    d_a = {"root": "the root"}
    d_b = {"dist_name": "george"}
    ReadPyprojectStrict().update(d_a, d_b)
    assert "dist_name" in d_a


@pytest.mark.logging_package_name(g_app_name)
@pytest.mark.parametrize(
    (
        "toml_contents, tool_name, key_name, expectation, "
        "expected_section_items_count"
    ),
    (
        pytest.param(
            (
                "[project]\n"
                """name = 'whatever'\n"""
                """version = '0.0.1'\n"""
                "[[tool.wreck.venvs]]\n"
                """venv_base_path = '.doc/.venv'\n"""
                "reqs = [\n"
                """   'docs/pip-tools',\n"""
                """   'docs/requirements',\n"""
                "]\n"
                "[[tool.wreck.venvs]]\n"
                """venv_base_path = '.venv'\n"""
                "reqs = [\n"
                """   'requirements/pip-tools',\n"""
                """   'requirements/pip',\n"""
                """   'requirements/prod.shared',\n"""
                """   'requirements/kit',\n"""
                """   'requirements/tox',\n"""
                """   'requirements/mypy',\n"""
                """   'requirements/manage',\n"""
                """   'requirements/dev',\n"""
                "]\n"
            ),
            f"{g_app_name}.venvs",
            "venv_base_path",
            does_not_raise(),
            2,
            id="two-items",
        ),
        pytest.param(
            (
                "[project]\n"
                """name = 'whatever'\n"""
                """version = '0.0.1'\n"""
                "[[tool.wreck.venvs]]\n"
                """venv_base_path = '.doc/.venv'\n"""
                "reqs = [\n"
                """   'docs/pip-tools',\n"""
                """   'docs/requirements',\n"""
                "]\n"
                "[[tool.wreck.venvs]]\n"
                """venv_base_path = '.venv'\n"""
                "reqs = [\n"
                """   'requirements/pip-tools',\n"""
                """   'requirements/pip',\n"""
                """   'requirements/prod.shared',\n"""
                """   'requirements/kit',\n"""
                """   'requirements/tox',\n"""
                """   'requirements/mypy',\n"""
                """   'requirements/manage',\n"""
                """   'requirements/dev',\n"""
                "]\n"
                "[[tool.wreck.venvs]]\n"
                """venv_base_path = '.doc/.venv'\n"""
                "reqs = [\n"
                """   'docs/pip-tools',\n"""
                """   'docs/requirements',\n"""
                "]\n"
            ),
            f"{g_app_name}.venvs",
            "venv_base_path",
            does_not_raise(),
            2,
            id="3rd-item-updates-1st",
        ),
        pytest.param(
            (
                "[project]\n"
                """name = 'whatever'\n"""
                """version = '0.0.1'\n"""
                "[tool.wreck.venvs]\n"
                """venv_base_path = '.doc/.venv'\n"""
            ),
            f"{g_app_name}.venvs",
            "venv_base_path",
            pytest.raises(LookupError),
            0,
            id="one-table-rather-than-array-of-tables.-Result-would-not-be-a-list",
        ),
    ),
)
def test_toml_array_of_tables(
    toml_contents: str,
    tool_name: str,
    key_name: str,
    expectation: "DOES_NOT_OR_DOES",
    expected_section_items_count: int,
    tmp_path: "Path",
    logging_strict: "Callable[[], tuple[logging.Logger, Sequence[logging.Logger]]]",
) -> None:
    """Support list[dict]"""
    # pytest --showlocals -vv --log-level INFO -k "test_toml_array_of_tables" tests
    t_two = logging_strict()
    logger, loggers = t_two

    # prepare
    #    Normally files are copied, not contents written
    path_f = tmp_path / "pyproject.toml"
    path_f.write_text(toml_contents)

    with expectation:
        data_1 = ReadPyproject()(
            path=path_f,
            tool_name=tool_name,
            key_name=key_name,
            is_expect_list=True,
        )
    if isinstance(expectation, does_not_raise):
        assert isinstance(data_1, PyProjectData)

        section_items = data_1.section
        actual_count = len(section_items)
        assert actual_count == expected_section_items_count

    # assert has_logging_occurred(caplog)
    pass


@pytest.mark.parametrize(
    "str_in, d_expected",
    (
        pytest.param(
            None,
            {},
            id="None",
        ),
        pytest.param(
            "",
            {},
            id="Empty-str",
        ),
        pytest.param(
            "    ",
            {},
            id="nonsense-white-space.-Actually-empty-str",
        ),
        pytest.param(
            '{project = {name = "proj", version = "0.0.1"}}',
            {"project": {"name": "proj", "version": "0.0.1"}},
            id="TOML-str-embedded-within-a-inline-dict",
        ),
        pytest.param(
            ("""[project]\n""" """name = 'proj'\n""" """version = '0.0.1'\n"""),
            {"project": {"name": "proj", "version": "0.0.1"}},
            id="Actual-TOML-data",
        ),
    ),
)
def test_load_toml_or_inline_map(
    str_in: "Union[str, None]",
    d_expected: dict[str, dict[str, str]],
) -> None:
    """Test load_toml_or_inline_map can take Any and smile."""
    # pytest --showlocals -vv --log-level INFO -k "test_load_toml_or_inline_map" tests
    d_actual = load_toml_or_inline_map(str_in)
    assert d_actual == d_expected
