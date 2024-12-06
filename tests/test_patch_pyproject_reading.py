"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Unit test -- Module

.. code-block:: shell

   python -m coverage run --source='wreck.monkey.patch_pyproject_reading' -m pytest \
   --showlocals tests/test_patch_pyproject_reading.py && coverage report \
   --data-file=.coverage --include="**/monkey/patch_pyproject_reading.py"

"""

import logging
import logging.config
import sys
from contextlib import nullcontext as does_not_raise
from pathlib import (
    Path,
    PurePath,
)

import pytest

from wreck.constants import (
    LOGGING,
    g_app_name,
)
from wreck.monkey.patch_pyproject_reading import (
    PyProjectData,
    ReadPyproject,
    ReadPyprojectStrict,
)
from wreck.monkey.pyproject_reading import load_toml_or_inline_map

if sys.version_info >= (3, 11):  # pragma: no cover py-gte-311-else
    import tomllib
else:  # pragma: no cover py-gte-311
    import tomli as tomllib


testdata_pyproject_data = (
    (
        "hope",
        {},
        {"name": "bob"},
        "bob",
    ),
)
ids_pyproject_data = ("empty section, pyproject.toml contains only name",)


@pytest.mark.parametrize(
    "tool_name, section, project, expected",
    testdata_pyproject_data,
    ids=ids_pyproject_data,
)
def test_pyproject_data(tool_name, section, expected, project, tmp_path):
    """From pyproject.toml confirm can get project name."""
    data = PyProjectData(tmp_path, tool_name, project, section)
    assert data.project_name == expected


testdata_read_pyproject_normal = (
    (
        "drain-swamp",
        Path(__file__).parent.joinpath(
            "_good_files",
            "complete-manage-pip-prod-unlock.pyproject_toml",
        ),
        does_not_raise(),
        "drain-swamp",
    ),
    (
        ("drain-swamp", "pipenv-unlock"),
        Path(__file__).parent.joinpath(
            "_good_files",
            "complete-manage-pip-prod-unlock.pyproject_toml",
        ),
        does_not_raise(),
        "drain-swamp",
    ),
    (
        "drain-swamp",
        Path(__file__).parent.joinpath(
            "_unsynced",
            "unsynced_1.lock",
        ),
        pytest.raises(tomllib.TOMLDecodeError),
        "drain-swamp",
    ),
)
ids_read_pyproject_normal = (
    "tool_name str",
    "tool_name Sequence[str]",
    "not a toml file",
)


@pytest.mark.parametrize(
    "tool_name, p_toml_file, expectation, expected_tool_name",
    testdata_read_pyproject_normal,
    ids=ids_read_pyproject_normal,
)
def test_read_pyproject_normal(
    tool_name,
    p_toml_file,
    expectation,
    expected_tool_name,
    tmp_path,
    prep_pyproject_toml,
):
    """Call ReadPyproject __call__. Pass in kwargs."""
    # pytest --showlocals -vv --log-level INFO -k "test_read_pyproject_normal" tests
    # prepare
    prep_pyproject_toml(p_toml_file, tmp_path)

    with expectation:
        data = ReadPyproject()(path=p_toml_file, tool_name=tool_name)
    if isinstance(expectation, does_not_raise):
        assert issubclass(type(data.path), PurePath)
        assert isinstance(data.tool_name, str)
        assert isinstance(data.section, dict)
        assert isinstance(data.project, dict)
        assert data.path == p_toml_file
        assert data.tool_name == expected_tool_name


testdata_read_pyproject_copyright_and_version = (
    (
        "Bob",
        Path(__file__).parent.joinpath(
            "_good_files",
            "full-course-meal-and-shower.pyproject_toml",
        ),
        pytest.raises(LookupError),
        False,
        False,
    ),
    (
        "Bob",
        Path(__file__).parent.joinpath(
            "_good_files",
            "complete-manage-pip-prod-unlock.pyproject_toml",
        ),
        pytest.raises(LookupError),
        False,
        False,
    ),
    (
        "pipenv-unlock",
        Path(__file__).parent.joinpath(
            "_good_files",
            "complete-manage-pip-prod-unlock.pyproject_toml",
        ),
        does_not_raise(),
        True,
        False,
    ),
    (
        ["drain-swamp", "pipenv-unlock"],
        Path(__file__).parent.joinpath(
            "_good_files",
            "complete-manage-pip-prod-unlock.pyproject_toml",
        ),
        does_not_raise(),
        True,
        True,
    ),
)
ids_read_pyproject_copyright_and_version = (
    "Nonexistant pyproject.toml",
    "No such section [tool.Bob]",
    "str",
    "Sequence[str]",
)


@pytest.mark.parametrize(
    "tool_name, p_toml_file, expectation, in_keys_version_file, in_keys_copyright",
    testdata_read_pyproject_copyright_and_version,
    ids=ids_read_pyproject_copyright_and_version,
)
def test_read_pyproject_copyright_and_version(
    tool_name,
    p_toml_file,
    expectation,
    in_keys_version_file,
    in_keys_copyright,
):
    """ReadPyproject __call__ exceptions."""
    # pytest --showlocals -vv --log-level INFO -k "test_read_pyproject_copyright_and_version" tests
    with expectation:
        data_1 = ReadPyproject()(path=p_toml_file, tool_name=tool_name)
    if isinstance(expectation, does_not_raise):
        assert isinstance(data_1.project, dict)
        assert isinstance(data_1.section, dict)
        assert data_1.project_name == "complete-awesome-perfect"
        keys = data_1.section.keys()
        #    from section drain-swamp
        assert in_keys_copyright == ("copyright_start_year" in keys)
        #    from section pipenv-unlock
        assert in_keys_version_file == ("version_file" in keys)


def test_update_dict_strict():
    """Update a ReadPyprojectStrict dict."""
    # pytest --showlocals -vv --log-level INFO -k "test_update_dict_strict" tests
    d_a = {"root": "the root"}
    d_b = {"dist_name": "george"}
    ReadPyprojectStrict().update(d_a, d_b)
    assert "dist_name" in d_a.keys()


testdata_toml_array_of_tables = (
    (
        (
            "[project]\n"
            """name = 'whatever'\n"""
            """version = '0.0.1'\n"""
            "[[tool.venvs]]\n"
            """venv_base_path = '.doc/.venv'\n"""
            "reqs = [\n"
            """   'docs/pip-tools',\n"""
            """   'docs/requirements',\n"""
            "]\n"
            "[[tool.venvs]]\n"
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
        "venvs",
        "venv_base_path",
        does_not_raise(),
        2,
    ),
    (
        (
            "[project]\n"
            """name = 'whatever'\n"""
            """version = '0.0.1'\n"""
            "[[tool.venvs]]\n"
            """venv_base_path = '.doc/.venv'\n"""
            "reqs = [\n"
            """   'docs/pip-tools',\n"""
            """   'docs/requirements',\n"""
            "]\n"
            "[[tool.venvs]]\n"
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
            "[[tool.venvs]]\n"
            """venv_base_path = '.doc/.venv'\n"""
            "reqs = [\n"
            """   'docs/pip-tools',\n"""
            """   'docs/requirements',\n"""
            "]\n"
        ),
        "venvs",
        "venv_base_path",
        does_not_raise(),
        2,
    ),
    (
        (
            "[project]\n"
            """name = 'whatever'\n"""
            """version = '0.0.1'\n"""
            "[tool.venvs]\n"
            """venv_base_path = '.doc/.venv'\n"""
        ),
        "venvs",
        "venv_base_path",
        pytest.raises(LookupError),
        0,
    ),
)
ids_toml_array_of_tables = (
    "two items",
    "3rd item updates 1st",
    "one table rather than array of tables. Result would not be a list",
)


@pytest.mark.parametrize(
    ("toml_contents, tool_name, key_name, expection, " "expected_section_items_count"),
    testdata_toml_array_of_tables,
    ids=ids_toml_array_of_tables,
)
def test_toml_array_of_tables(
    toml_contents,
    tool_name,
    key_name,
    expection,
    expected_section_items_count,
    tmp_path,
    caplog,
    has_logging_occurred,
):
    """Support list[dict]"""
    # pytest --showlocals -vv --log-level INFO -k "test_toml_array_of_tables" tests
    LOGGING["loggers"][g_app_name]["propagate"] = True
    logging.config.dictConfig(LOGGING)
    logger = logging.getLogger(name=g_app_name)
    logger.addHandler(hdlr=caplog.handler)
    caplog.handler.level = logger.level

    # prepare
    #    Normally files are copied, not contents written
    path_f = tmp_path / "pyproject.toml"
    path_f.write_text(toml_contents)

    with expection:
        data_1 = ReadPyproject()(
            path=path_f,
            tool_name=tool_name,
            key_name=key_name,
            is_expect_list=True,
        )
    if isinstance(expection, does_not_raise):
        assert isinstance(data_1, PyProjectData)

        section_items = data_1.section
        actual_count = len(section_items)
        assert actual_count == expected_section_items_count

    # assert has_logging_occurred(caplog)
    pass


testdata_load_toml_or_inline_map = (
    (
        None,
        {},
    ),
    (
        "",
        {},
    ),
    (
        "    ",
        {},
    ),
    (
        '{project = {name = "proj", version = "0.0.1"}}',
        {"project": {"name": "proj", "version": "0.0.1"}},
    ),
    (
        ("""[project]\n""" """name = 'proj'\n""" """version = '0.0.1'\n"""),
        {"project": {"name": "proj", "version": "0.0.1"}},
    ),
)
ids_load_toml_or_inline_map = (
    "None",
    "Empty str",
    "nonsense white space. Actually empty str",
    "TOML str embedded within a inline dict",
    "Actual TOML data",
)


@pytest.mark.parametrize(
    "str_in, d_expected",
    testdata_load_toml_or_inline_map,
    ids=ids_load_toml_or_inline_map,
)
def test_load_toml_or_inline_map(str_in, d_expected):
    """Test load_toml_or_inline_map can take Any and smile."""
    # pytest --showlocals -vv --log-level INFO -k "test_load_toml_or_inline_map" tests
    d_actual = load_toml_or_inline_map(str_in)
    assert d_actual == d_expected
