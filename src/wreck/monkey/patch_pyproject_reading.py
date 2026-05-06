"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

In module :ref:`setuptools-scm-code-pyproject_reading` function
read_pyproject is too strict, monkeypatch it!

Without the patch, ``pyproject.toml`` [tool.setuptools-scm] section is
missing, raises :py:exc:`LookupError`.

.. warning:: tool_name ordering

   tool_name requires 1st [tool.x] section to be the package name, in
   this case, drain-swamp. e.g. [tool.drain-swamp] section

**CHANGES**

- tool_name (str -> str | Sequence[str])
  from "setuptools-scm"
  to ["drain-swamp"]

- the tool_name becomes the first element

- combines contents of sections

.. py:data:: __all__
   :type: tuple[str, str]
   :value: ("ReadPyproject", "ReadPyprojectStrict")

   Module exports

.. py:data:: log
   :type: logging.Logger

   module level logger

.. py:data:: is_module_debug
   :type: bool
   :value: False

   Turn on during debugging

"""

from __future__ import annotations

import abc
import copy
import logging
from collections.abc import (
    Mapping,
    Sequence,
)
from pathlib import Path
from typing import NamedTuple

from ..check_type import is_ok
from ..constants import g_app_name
from .pyproject_reading import (
    TOML_RESULT,
    read_toml_content,
)

log = logging.getLogger(f"{g_app_name}.monkey.patch_pyproject_reading")
is_module_debug = False

__all__ = (
    "ReadPyproject",
    "ReadPyprojectStrict",
)


class PyProjectData(NamedTuple):
    """Data class for holding contents of a section.

    :cvar path: config file Path
    :vartype path: pathlib.Path
    :cvar tool_name: section name
    :vartype tool_name: str
    :cvar project: Project section contents
    :vartype project: wreck.monkey.pyproject_reading.TOML_RESULT
    :cvar section: Section contents
    :vartype section: wreck.monkey.pyproject_reading.TOML_RESULT | collections.abc.Sequence[wreck.monkey.pyproject_reading.TOML_RESULT]
    :cvar section_parent:

       Read only and scalars only. Get configuration options from parent section

    :vartype section_parent: wreck.monkey.pyproject_reading.TOML_RESULT
    """

    path: Path
    tool_name: str
    project: TOML_RESULT
    section: TOML_RESULT | Sequence[TOML_RESULT]
    section_parent: TOML_RESULT

    @property
    def project_name(self):
        """Getter for project.name

        :returns: package name
        :rtype: str | None
        """
        return self.project.get("name")


class ReadPyprojectBase(abc.ABC):
    """From a pyproject.toml file, ABC for key/value pairs from a section."""

    @abc.abstractmethod
    def update(
        self,
        d_target,
        d_other,
        key_name: str | None = None,
        key_value: str | None = None,
    ):
        """Subclass overload so can filter d_other.

        :param d_target: parent dict
        :type d_target: wreck.monkey.pyproject_reading.TOML_RESULT | collections.abc.Sequence[wreck.monkey.pyproject_reading.TOML_RESULT]
        :param d_other: dict. Update parent
        :type d_other: wreck.monkey.pyproject_reading.TOML_RESULT
        :param key_name:

           None if not a ``collections.abc.Sequence[dict]``. To identify
           which dict to update, a known dict key is searched for.

        :type key_name: str | None
        :param key_value:

           None if not a ``collections.abc.Sequence[dict]``. To identify
           which dict to update, a known dict key / value pair are used
           to find a match.

        :type key_value: str | None
        """
        ...

    def __call__(
        self,
        path=Path("pyproject.toml"),
        tool_name=["drain-swamp"],
        require_section=True,
        key_name: str | None = None,
        is_expect_list: bool = False,
    ):
        """Read in pyproject.toml and if necessary combine multiple sections into one.

        Previously raised :py:exc:`FileNotFoundError` and :py:exc:`LookupError`
        instead will produce an empty dict

        :param path: Defaults to :code:`Path("pyproject.toml")` Absolute path to toml file
        :type path: pathlib.Path
        :param tool_name:

           Default ``["drain-swamp"]``. ``pyproject.toml``
           sections name or section name. First section name **MUST** be the package name

        :type tool_name: str | Sequence[str]
        :param require_section:

           Default True. This is ignored. Prevents extending package
           features and the possibility of pulling in multiple sections

        :type require_section: bool
        :param key_name:

           None if not a ``collections.abc.Sequence[dict]``. To identify
           which dict to update, a known dict key is searched for.

        :type key_name: str | None
        :param is_expect_list:

           Default False. Do not accept a TOML table (dict) when want
           a TOML array of tables list[dict]

        :type is_expect_list: bool
        :returns: A convenience representation of ``pyproject.toml`` file
        :rtype: PyProjectData
        :raises:

           - :py:exc:`FileNotFoundError` -- pyproject.toml not found

           - :py:exc:`LookupError` -- Either toml file parsing failed
             or no such section

           - :py:exc:`KeyError` -- pyproject.toml section not found

        .. todo::

           Do a reverse search for the pyproject.toml file

        """
        mod_path = "wreck.monkey.patch_pyproject_reading.ReadPyprojectBase.__call__"
        if isinstance(tool_name, str):
            seq_tool = (tool_name,)
        else:
            # assumes a Sequence[str]
            seq_tool = tool_name

        try:
            defn = read_toml_content(path)
        except FileNotFoundError:
            # None if require_section else {}
            defn = {}

        if is_module_debug:  # pragma: no branch  # pragma: no cover
            msg_info = f"In {mod_path}, toml contents {defn}"
            log.info(msg_info)

        # Combine sections
        # Was preventing extending setuptools_scm
        d_section: TOML_RESULT = {}
        d_section_parent: TOML_RESULT = {}
        lst_section: Sequence[TOML_RESULT] = []
        is_section_dict = False
        # multiple tool -- do not get section_parent
        is_single_tool = len(seq_tool) == 1
        # remove tool_name that is: not a str, or empty string or just whitespace
        seq_tool_clean = [tool_name for tool_name in seq_tool if is_ok(tool_name)]
        msgs = []
        for tool_name in seq_tool_clean:
            name_keys = tool_name.split(".")
            section = {}
            try:
                for idx, key in enumerate(name_keys):
                    is_section_first = idx == 0

                    if is_section_first:
                        # no period. e.g. 'wreck'. Implies 'tool.wreck' or first period
                        # Does not have a parent section
                        section = defn.get("tool", {})[key]
                    else:
                        # Subsequent periods
                        #    get section parent
                        if is_single_tool:
                            d_section_cpy = copy.deepcopy(section)
                            d_section_cpy.pop(key, None)
                            d_section_parent = d_section_cpy
                        else:  # pragma: no cover
                            pass
                        #    get section
                        section = section.get(key, {})
            except (KeyError, LookupError) as e:
                error = f"{path} does not contain a tool.{tool_name} section"
                msg_warn = f"toml section missing {error!r}"
                # log.warning(msg_warn, exc_info=True)
                raise LookupError(msg_warn) from e
            # subclass must implement method, ``update``

            if is_module_debug:  # pragma: no branch  # pragma: no cover
                msg_info = f"In {mod_path}, section {type(section)}"
                log.info(msg_info)

            is_key_name_ok = (
                key_name is not None
                and isinstance(key_name, str)
                and len(key_name.strip()) != 0
            )

            if isinstance(section, Mapping) and not is_expect_list:
                self.update(d_section, section)
                is_section_dict = True
            elif isinstance(section, Sequence):
                if not is_key_name_ok:
                    # No key provided. Update will not occur
                    pass
                else:
                    # Key provided. Update key/value pair
                    for d_item in section:
                        if is_module_debug:  # pragma: no branch  # pragma: no cover
                            msg_info = f"In {mod_path}, call update(before) {d_item}"
                            log.info(msg_info)

                        self.update(
                            lst_section,
                            d_item,
                            key_name=key_name,
                            key_value=d_item[key_name],
                        )

                        if is_module_debug:  # pragma: no branch  # pragma: no cover
                            msg_info = (
                                f"In {mod_path}, call update(after) {lst_section}"
                            )
                            log.info(msg_info)

                    if is_module_debug:  # pragma: no branch  # pragma: no cover
                        msg_info = f"In {mod_path}, finally {lst_section}"
                        log.info(msg_info)
            else:  # pragma: no cover
                msg_warn = (
                    f"In {path!s} tool.{tool_name} section expected either "
                    f"a list or a dict. Got {section!r}"
                )
                msgs.append(msg_warn)

        if bool(msgs):  # pragma: no branch
            str_msgs = "\n".join(msgs)
            raise LookupError(str_msgs)

        project = defn.get("project", {})

        # Use 1st tool name
        tool_name_2: str = seq_tool[0]

        if is_section_dict:
            section_mixed = d_section
        else:
            section_mixed = lst_section

        ret = PyProjectData(path, tool_name_2, project, section_mixed, d_section_parent)

        return ret


class ReadPyproject(ReadPyprojectBase):
    """Do not confine data fields. Accept whatever the section(s) contains."""

    def update(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        mixed_target,
        d_other,
        key_name: str | None = None,
        key_value: str | None = None,
    ):
        """Update a ReadPyprojectBase subclass instance. Which is either
        a dict or a list[dict].

        For list[dict] also supply a key / value pair. So know which dict to update.

        :param mixed_target: parent dict
        :type mixed_target: dict[str, typing.Any] | list[dict[str, typing.Any]]
        :param d_other: dict. Update parent
        :type d_other: dict[str, typing.Any]
        :param key_name:

           None if not a ``collections.abc.Sequence[dict]``. To identify
           which dict to update, a known dict key is searched for.

        :type key_name: str | None
        :param key_value:

           None if not a ``collections.abc.Sequence[dict]``. To identify
           which dict to update, a known dict key / value pair are used
           to find a match.

        :type key_value: str | None
        """
        if isinstance(mixed_target, dict) and isinstance(d_other, Mapping):
            mixed_target.update(d_other)
        elif isinstance(mixed_target, list) and isinstance(d_other, Mapping):
            # Check for match. If no match append.
            is_found = any(
                [d_item.get(key_name, "") == key_value for d_item in mixed_target]
            )

            if not is_found:
                # new section
                mixed_target.append(d_other)
            else:
                # update section
                #    Known match exists
                for idx, d_item in enumerate(mixed_target):
                    is_match = d_item.get(key_name, "") == key_value
                    if is_match:  # pragma: no branch
                        d_item.update(d_other)
                        mixed_target[idx] = d_item


class ReadPyprojectStrict(ReadPyprojectBase):
    """Confine data fields to acceptable by setuptools_scm._config.Configuration."""

    def update(
        self,
        d_target,
        d_other,
        key_name: str | None = None,
        key_value: str | None = None,
    ):
        """Confine to only setuptools_scm._config.Configuration data fields.

        Parent cannot be a ``list[dict]``.

        :param d_target: parent dict
        :type d_target: dict[str, typing.Any]
        :param d_other: dict. Update parent
        :type d_other: dict[str, typing.Any]
        :param key_name: Default None. Ignored
        :type key_name: str | None
        :param key_value: Default None. Ignored
        :type key_value: str | None
        """
        # import dataclasses
        # from setuptools_scm._config import Configuration
        # [field.name for field in fields(Configuration)]
        keys_allowed = (
            "relative_to",
            "root",
            "version_scheme",
            "local_scheme",
            "tag_regex",
            "parentdir_prefix_version",
            "fallback_version",
            "fallback_root",
            "write_to",
            "write_to_template",
            "version_file",
            "version_file_template",
            "parse",
            "git_describe_command",
            "dist_name",
            "version_cls",
            "search_parent_directories",
            "parent",
        )
        # dict comprehension to filter dict keys
        d_y = {k: v for k, v in d_other.items() if k in keys_allowed}
        d_target.update(d_y)
