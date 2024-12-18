"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Separate out ``.in`` processing from ``.unlock`` and ``.lock`` implementations

.. py:data:: __all__
   :type: tuple[str, str, str]
   :value: ("strip_inline_comments", "InFile", "InFiles")

.. py:data:: _logger
   :type: logging.Logger

   Module level logger

.. py:data:: is_module_debug
   :type: bool
   :value: False

   on/off for module level logging

.. deprecated:: 0.1.0
   Instead use :py:class:`wreck.lock_collections.Ins`

   InFiles reads each .in files multiple times, not once

   Left here until dependency resolution is removed from package drain-swamp

"""

import copy
import dataclasses
import logging
import os
import pathlib
from collections.abc import (
    Hashable,
    Sequence,
)
from pathlib import (
    Path,
    PurePath,
)
from typing import cast

from ._safe_path import resolve_joinpath
from .constants import (
    SUFFIX_UNLOCKED,
    g_app_name,
)
from .exceptions import MissingRequirementsFoldersFiles
from .lock_datum import (
    InFileType,
    in_generic,
)
from .lock_util import (
    check_relpath,
    is_shared,
    is_suffixes_ok,
    replace_suffixes_last,
)

_logger = logging.getLogger(f"{g_app_name}.lock_infile")
is_module_debug = False
__all__ = (
    "strip_inline_comments",
    "InFile",
    "InFiles",
)


def strip_inline_comments(val):
    """Strip off inline comments. Which may be to the right of a requirement

    :param val: line with contains a requirement and optionally an in-line comment
    :type val: str
    :returns: Requirement without a inline comment
    :rtype: str
    """
    try:
        pos = val.index("#")
    except ValueError:
        # not found
        ret = val
    else:
        ret = val[:pos]
        ret = ret.rstrip()

    return ret


@dataclasses.dataclass
class InFile(Hashable):
    """Represents one ``.in`` file. Which *may contain* constraints
    ``-c`` and requirements ``-r`` line(s).

    :ivar relpath: Relative path to requirements file
    :vartype relpath: str
    :ivar stem:

       Requirements file stem. Later, appends suffix ``.unlock``

    :vartype stem: str
    :ivar constraints:

       Requirement files may contain lines starting with
       ``-c [requirements file relative path]``. This constitutes a
       constraint. The requirements file referenced by a constraint, can
       also contain constraints. The tree of constraints is resolved
       recursively until all constraints on all requirements files are resolved.

    :vartype constraints: set[str]
    :ivar requirements:

       Contains all dependencies from a requirements file. There is no
       attempt made to resolve package versions.

    :vartype requirements: set[str]
    :raises:

       - :py:exc:`ValueError` -- relpath or stem have issues or unrelated

    """

    relpath: str
    stem: str
    constraints: set[str] = dataclasses.field(default_factory=set)
    requirements: set[str] = dataclasses.field(default_factory=set)

    def __post_init__(self):
        """relpath given as a Path, convert into a str.
        :py:func:`wreck.lock_util.check_relpath` should
        have already been performed/called prior
        """
        # Remove ambiguity. relpath should contain at least one suffix
        try:
            path_f = is_suffixes_ok(self.relpath)
        except (ValueError, TypeError):
            raise
        else:
            self.relpath = str(path_f)

        # Check stem
        is_stem_not_in = self.stem not in self.relpath
        is_stem_eq_name = self.stem == Path(self.relpath).name
        is_stem_ng = is_stem_not_in or is_stem_eq_name
        if is_stem_ng:
            msg_warn = (
                f"InFile.stem {self.stem} has no relation to "
                f"InFile.relpath {self.relpath}. Fix it"
            )
            raise ValueError(msg_warn)
        else:  # pragma: no cover
            pass

    def abspath(self, path_package_base):
        """Get the absolute path. The relative path is relative to the
        package folder.

        :param path_package_base: package base folder
        :type path_package_base: pathlib.Path
        :returns: absolute path
        :rtype: pathlib.Path
        """
        return path_package_base.joinpath(self.relpath)

    @property
    def depth(self):
        """Number of unresolved constraints. One this number gets down
        to zero, the InFile is moved from files set --> zeroes set

        :returns: unresolved constraints count
        :rtype: int
        """
        return len(self.constraints)

    def resolve(self, constraint, requirements):
        """
        :param constraint: A ``.in`` file relative path
        :type constraint: str
        :param requirements:

           The ``.in`` file's requirement lines, which might have silly
           version upper limits. No attempt is made to address these
           upper bounds version limits

        :type requirements: set[str]
        """
        self.constraints.remove(constraint)

        # Removes duplicates, but ignores version constraints
        for req in requirements:
            self.requirements.add(req)

    def __hash__(self):
        """Constraints as constraints are resolved, are removed,
        increasing the requirements.

        Both fields are dynamic. For the point of identification,
        the relpath is unique

        :returns: hash of relpath
        :rtype: int
        """
        return hash((self.relpath,))

    def __eq__(self, right):
        """Compares equality

        :param right: right side of the equal comparison
        :type right: typing.Any
        :returns:

           True if both are same InFile otherwise False. Does not take
           in account, constraints and requirements.

        :rtype: bool
        """
        is_infile = isinstance(right, InFile)
        is_str = isinstance(right, str)
        is_relpath = issubclass(type(right), PurePath) and not right.is_absolute()
        if is_relpath:
            str_right = str(right)
        elif is_str:
            str_right = right
        else:  # pragma: no cover
            pass

        if is_infile:
            is_eq = self.__hash__() == right.__hash__()
            ret = is_eq
        elif is_str or is_relpath:
            # relpath
            left_hash = hash(self)
            right_hash = hash((str_right,))
            is_eq = left_hash == right_hash
            ret = is_eq
        else:
            ret = False

        return ret

    def __lt__(self, right):
        """Try comparing using stem. If both A and B have the same
        stem. Compare using relpath

        Implementing __hash__, __eq__, and __lt__ is the minimal
        requirement for supporting the python built-tin sorted method

        :param right: right side of the comparison
        :type right: typing.Any
        :returns: True if A < B otherwise False
        :rtype: bool
        :raises:

           - :py:exc:`TypeError` -- right operand is unsupported type

        """
        is_ng = right is None or not isinstance(right, InFile)
        if is_ng:
            msg_warn = f"Expecting an InFile got unsupported type {type(right)}"
            raise TypeError(msg_warn)
        else:  # pragma: no cover
            pass

        # InFiles container stores InFile within a set. So no duplicates
        # Compares tuple(stem_a, relpath_a) vs tuple(stem_b, relpath_b)
        is_stem_eq = self.stem == right.stem
        if not is_stem_eq:
            is_lt = self.stem < right.stem
        else:
            # stems match so compare entire relpath
            is_lt = self.relpath < right.relpath

        return is_lt


@dataclasses.dataclass
class InFiles:
    """Container of InFile

    :ivar cwd: current working directory
    :vartype cwd: pathlib.Path
    :ivar in_files: Requirements files. Relative path to ``.in`` files
    :vartype in_files: collections.abc.Sequence[pathlib.Path]
    :ivar _files:

       Set of InFile. Which contains the relative path to a Requirement
       file. May contain unresolved constraints

    :vartype _files: set[InFile]
    :ivar _zeroes: Set of InFile that have all constraints resolved
    :vartype _zeroes: set[InFile]

    :raises:

       - :py:exc:`TypeError` -- in_files unsupported type, expecting
         ``Sequence[Path]``

       - :py:exc:`ValueError` -- An element within in_files is not
         relative to folder, cwd

       - :py:exc:`FileNotFoundError` -- Requirements .in file not found

       - :py:exc:`wreck.exceptions.MissingRequirementsFoldersFiles` --
         A requirements file references a nonexistent constraint

    """

    cwd: pathlib.Path
    in_files: dataclasses.InitVar[Sequence[pathlib.Path]]
    _files: set[InFile] = dataclasses.field(init=False, default_factory=set)
    _zeroes: set[InFile] = dataclasses.field(init=False, default_factory=set)

    def __post_init__(self, in_files):
        """Read in and initial pass over ``.in`` files

        :param in_files: Requirements files. Relative path to ``.in`` files
        :type in_files: collections.abc.Sequence[pathlib.Path]
        """
        # is a sequence
        if in_files is None or not isinstance(in_files, Sequence):
            msg_exc = f"Expecting a list[Path] got unsupported type {in_files}"
            raise TypeError(msg_exc)

        for path_abs in in_files:
            self.files = path_abs

    @staticmethod
    def line_comment_or_blank(line):
        """Comments or blank lines can be safely ignored

        :param line: .in file line to check if inconsequential
        :type line: str
        :returns: True if a line which can be safely ignored otherwise False
        :rtype: bool
        """
        is_comment = line.startswith("#")
        is_blank_line = len(line.strip()) == 0
        return is_comment or is_blank_line

    @staticmethod
    def is_requirement_or_constraint(line):
        """Line identify if a requirement (-r) or constraint (-c)

        :param line: .in file line is a file which should be included
        :type line: str
        :returns: True if a line needs to be included otherwise False
        :rtype: bool
        """
        return line.startswith("-c ") or line.startswith("-r ")

    @property
    def files(self):
        """Generator of sorted InFile

        :returns: Yields InFile. These tend to contain constraints
        :rtype: collections.abc.Generator[wreck.lock_infile.InFile, None, None]
        """
        yield from sorted(self._files)

    @files.setter
    def files(self, val):
        """Append an InFile, requirement or constraint

        :param val:

           :py:class:`~wreck.lock_infile.InFile` or absolute path
           to requirement or constraint file

        :type val: typing.Any
        """
        mod_path = f"{g_app_name}.lock_infile.InFiles.files"
        is_abspath = (
            val is not None
            and issubclass(type(val), PurePath)
            and val.is_absolute()
            and val.exists()
            and val.is_file()
        )
        if is_abspath:
            cls = type(self)
            path_abs = val
            try:
                check_relpath(self.cwd, path_abs)
            except (TypeError, ValueError, FileNotFoundError):  # pragma: no cover
                # Not Path and absolute so won't create InFile and add it to container
                msg_warn = f"{mod_path} Requirement file does not exist! {path_abs!r}"
                _logger.warning(msg_warn)
            else:
                path_relpath = path_abs.relative_to(self.cwd)
                str_file = path_abs.read_text()
                lines = str_file.split("\n")
                constraint_raw = []
                requirement = set()
                for line in lines:
                    if cls.line_comment_or_blank(line):
                        continue
                    elif cls.is_requirement_or_constraint(line):
                        # -r or -c are treated as equivalents
                        line_pkg = line[3:]
                        line_pkg = strip_inline_comments(line_pkg)
                        constraint_raw.append(line_pkg)
                    else:
                        """unknown pip file options, will be considered a requirement"""
                        line_pkg = strip_inline_comments(line)
                        requirement.add(line_pkg)

                """Normalize constraint
                Assume .in files constraints are relative path only
                """
                path_parent = path_abs.parent
                constraint = set()
                for cons_path in constraint_raw:
                    abspath_to_check = cast(
                        "Path",
                        resolve_joinpath(path_parent, cons_path),
                    )
                    try:
                        path_abs_constraint = abspath_to_check.resolve(strict=True)
                    except FileNotFoundError:
                        msg_warn = (
                            f"{mod_path} Constraint file does not exist! "
                            f"{abspath_to_check.resolve()}"
                        )
                        _logger.warning(msg_warn)
                        path_abs_constraint = abspath_to_check.resolve()
                        """
                        msg_exc = (
                            f"Within requirements file, {path_relpath}, a constraint "
                            f"file does not exist. Create it! {cons_path}"
                        )
                        raise MissingRequirementsFoldersFiles(msg_exc) from exc
                        """
                        pass

                    """Do not get to choose we don't like the constraint
                    cuz file not exists"""
                    path_rel_constraint = path_abs_constraint.relative_to(self.cwd)
                    constraint.add(str(path_rel_constraint))

                # Checks already performed for: TypeError, ValueError or FileNotFoundError
                in_ = InFile(
                    relpath=path_relpath,
                    stem=path_abs.stem,
                    constraints=constraint,
                    requirements=requirement,
                )
                if is_module_debug:  # pragma: no cover
                    msg_info = f"in_: {repr(in_)}"
                    _logger.info(msg_info)
                else:  # pragma: no cover
                    pass
                is_new = not self.in_zeroes(in_) and in_ not in self
                if is_new:
                    # Found a new constraint or requirement!
                    val = in_
                else:  # pragma: no cover
                    pass
        else:  # pragma: no cover
            pass

        is_infile = val is not None and isinstance(val, InFile)
        if is_infile:
            self._files.add(val)
        else:  # pragma: no cover
            pass

    @property
    def zeroes(self):
        """Generator of InFile

        :returns: Yields InFile without any constraints
        :rtype: collections.abc.Generator[wreck.lock_infile.InFile, None, None]
        """
        yield from self._zeroes

    @zeroes.setter
    def zeroes(self, val):
        """append an InFile that doesn't have any constraints

        The only acceptable source of zeroes is from :code:`self._files`

        :param val: Supposed to be an :py:class:`~wreck.lock_infile.InFile`
        :type val: typing.Any
        """
        is_infile = val is not None and isinstance(val, InFile)
        if is_infile:
            self._zeroes.add(val)
        else:  # pragma: no cover
            pass

    def in_generic(self, val, set_name=InFileType.FILES):
        """A generic __contains__

        :param val: item to check if within zeroes
        :type val: typing.Any
        :param set_name:

           Default :py:attr:`wreck.lock_datum.InFileType.FILES`.
           Which set to search thru. zeroes or files

        :type set_name: wreck.lock_datum.InFileType | None
        :returns: True if InFile contained within zeroes otherwise False
        :rtype: bool
        """
        if set_name is None or not isinstance(set_name, InFileType):
            str_set_name = str(InFileType.FILES)
        else:  # pragma: no cover
            str_set_name = str(set_name)

        """
        if is_module_debug:  # pragma: no cover
            msg_info = f"InFiles.in_generic InFile set name {str_set_name}"
            _logger.info(msg_info)
        else:  # pragma: no cover
            pass
        """
        pass

        ret = False
        set_ = getattr(self, str_set_name, set())
        for in_ in set_:
            if val is not None:
                is_match_infile = isinstance(val, InFile) and in_ == val
                is_match_str = isinstance(val, str) and in_.relpath == val

                is_match_path = issubclass(type(val), PurePath) and in_.relpath == str(
                    val
                )
                if is_match_infile or is_match_str or is_match_path:
                    ret = True
                else:  # pragma: no cover
                    # unsupported type
                    pass
            else:  # pragma: no cover
                # is None
                pass

        return ret

    def in_zeroes(self, val):
        """Check if within zeroes

        :param val: item to check if within zeroes
        :type val: typing.Any
        :returns: True if InFile contained within zeroes otherwise False
        :rtype: bool
        """
        # ret = self.in_generic(val, set_name=InFileType.ZEROES)
        ret = in_generic(
            self,
            val,
            "relpath",
            set_name=InFileType.ZEROES,
            is_abspath_ok=False,
        )

        return ret

    def __contains__(self, val):
        """Check if within InFiles

        :param val: item to check if within InFiles
        :type val: typing.Any
        :returns: True if InFile contained within InFiles otherwise False
        :rtype: bool
        """
        # ret = self.in_generic(val)
        ret = in_generic(
            self,
            val,
            "relpath",
            set_name=InFileType.FILES,
            is_abspath_ok=False,
        )
        return ret

    def get_by_relpath(self, relpath, set_name=InFileType.FILES):
        """Get the index and :py:class:`~wreck.lock_infile.InFile`

        :param relpath: relative path of a ``.in`` file
        :type relpath: str
        :param set_name:

           Default :py:attr:`wreck.lock_datum.InFileType.FILES`.
           Which set to search thru. zeroes or files.

        :type set_name: str | None
        :returns:

           The ``.in`` file and index within
           :py:class:`~wreck.lock_infile.InFiles`

        :rtype: wreck.lock_infile.InFile | None
        :raises:

            - :py:exc:`ValueError` -- Unsupported type. relpath is neither str nor Path

        """
        if set_name is None or not isinstance(set_name, InFileType):
            str_set_name = str(InFileType.FILES)
        else:  # pragma: no cover
            str_set_name = str(set_name)

        msg_exc = f"Expected a relative path as str or Path. Got {type(relpath)}"
        str_relpath = None
        if relpath is not None:
            if isinstance(relpath, str):
                str_relpath = relpath
            elif issubclass(type(relpath), PurePath):
                str_relpath = str(relpath)
            else:
                raise ValueError(msg_exc)
        else:
            raise ValueError(msg_exc)

        ret = None
        set_ = getattr(self, str_set_name, set())
        for in_ in set_:
            if in_.relpath == str_relpath:
                ret = in_
                break
            else:  # pragma: no cover
                # not a match
                pass
        else:
            # set empty
            ret = None

        return ret

    def move_zeroes(self):
        """Zeroes have had all their constraints resolved and therefore
        do not need to be further scrutinized.
        """
        # add to self.zeroes
        del_these = []
        for in_ in self.files:
            if in_.depth == 0:
                # set.add an InFile
                self.zeroes = in_
                del_these.append(in_)
            else:  # pragma: no cover
                pass

        if is_module_debug:  # pragma: no cover
            msg_info = f"self.zeroes (after): {self.zeroes}"
            _logger.info(msg_info)
        else:  # pragma: no cover
            pass

        # remove from self._files
        for in_ in del_these:
            self._files.remove(in_)

        if is_module_debug:  # pragma: no cover
            msg_info = f"self.files (after): {self.files}"
            _logger.info(msg_info)
        else:  # pragma: no cover
            pass

    def resolve_zeroes(self):
        """If a requirements file have constraint(s) that can be
        resolved, by a zero, do so.

        _files and _zeroes are both type, set. Modifying an element
        modifies element within the set
        """
        meth_path = f"{g_app_name}.lock_infile.InFiles.resolve_zeroes"
        # Take the win, early and often!
        self.move_zeroes()

        # Add if new constraint?
        abspath_cwd = self.cwd
        add_these = []
        for in_ in self.files:
            for constraint_relpath in in_.constraints:
                is_in_zeroes = self.in_zeroes(constraint_relpath)
                is_in_files = constraint_relpath in self
                is_new = not is_in_zeroes and not is_in_files
                if is_new:
                    abspath_constraint = cast(
                        "Path",
                        resolve_joinpath(abspath_cwd, constraint_relpath),
                    )
                    # Attempt to add the constraint to self._files
                    add_these.append(abspath_constraint)
                else:  # pragma: no cover
                    pass

        # Add new after iterator is exhausted
        for abspath_constraint in add_these:
            self.files = abspath_constraint

        # Any contraints zeroes?
        self.move_zeroes()

        # Resolve with zeroes
        for in_ in self.files:
            constaints_copy = copy.deepcopy(in_.constraints)
            for constraint_relpath in constaints_copy:
                is_in_zeroes = self.in_zeroes(constraint_relpath)
                is_in_files = constraint_relpath in self

                if is_module_debug:  # pragma: no cover
                    msg_info = (
                        f"{meth_path} constraint {constraint_relpath} "
                        f"in zeroes {is_in_zeroes} in files {is_in_files}"
                    )
                    _logger.info(msg_info)
                else:  # pragma: no cover
                    pass

                if is_in_zeroes:
                    # Raises ValueError if constraint_relpath is neither str nor Path
                    item = self.get_by_relpath(
                        constraint_relpath, set_name=InFileType.ZEROES
                    )

                    if is_module_debug:  # pragma: no cover
                        msg_info = f"{meth_path} in_ (before) {in_}"
                        _logger.info(msg_info)
                    else:  # pragma: no cover
                        pass

                    in_.resolve(constraint_relpath, item.requirements)

                    if is_module_debug:  # pragma: no cover
                        msg_info = f"{meth_path} in_ (after) {in_}"
                        _logger.info(msg_info)
                    else:  # pragma: no cover
                        pass
                else:  # pragma: no cover
                    pass

        # For an InFile, are all it's constraints resolved?
        self.move_zeroes()

    def resolution_loop(self):
        """Run loop of resolve_zeroes calls, sampling before and after
        counts. If not fully resolved and two iterations have the same
        result, raise an Exception

        :raises:

           - :py:exc:`wreck.exceptions.MissingRequirementsFoldersFiles` --
             there are unresolvable constraint(s)

        """
        meth_path = f"{g_app_name}.lock_infile.InFiles.resolution_loop"
        initial_count_files = len(list(self.files))
        initial_count_zeroes = len(list(self.zeroes))
        current_count_files = initial_count_files
        previous_count_files = initial_count_files
        current_count_zeroes = initial_count_zeroes
        previous_count_zeroes = initial_count_zeroes
        while current_count_files != 0:
            if is_module_debug:  # pragma: no cover
                msg_info = (
                    f"{meth_path} (before resolve_zeroes) resolution current "
                    f"state. previous_count files {previous_count_files} "
                    f"current count files {current_count_files} "
                    f"previous count zeroes {previous_count_zeroes} "
                    f"current count zeroes {current_count_zeroes} "
                    f"files {self._files}\n"
                    f"zeroes {self._zeroes}"
                )
                _logger.info(msg_info)
            else:  # pragma: no cover
                pass

            self.resolve_zeroes()
            current_count_files = len(list(self.files))
            current_count_zeroes = len(list(self.zeroes))
            # Check previous run results vs current run results, if same raise Exception
            is_resolved = current_count_files == 0
            is_result_same_files = previous_count_files == current_count_files
            is_result_same_zeroes = previous_count_zeroes == current_count_zeroes

            if is_module_debug:  # pragma: no cover
                msg_info = (
                    f"{meth_path} (after resolve_zeroes) "
                    "resolution current state. current count files "
                    f"{current_count_files} "
                    f"current count zeroes {current_count_zeroes} "
                    f"files {self._files}\n"
                    f"zeroes {self._zeroes}"
                )
                _logger.info(msg_info)
            else:  # pragma: no cover
                pass

            # raise exception if not making any progress
            is_result_same = is_result_same_files and is_result_same_zeroes
            if not is_resolved and is_result_same:
                unresolvable_requirement_files = [in_.relpath for in_ in self.files]
                missing_contraints = [in_.constraints for in_ in self.files]
                msg_warn = (
                    f"{meth_path} Missing .in requirements file(s). "
                    "Unable to resolve constraint(s). Files with "
                    f"unresolvable constraints: {unresolvable_requirement_files}. "
                    f"Missing constraints: {missing_contraints}"
                )
                _logger.warning(msg_warn)
                raise MissingRequirementsFoldersFiles(msg_warn)
            else:  # pragma: no cover
                pass

            previous_count_files = current_count_files
            previous_count_zeroes = current_count_zeroes

    def write(self):
        """After resolving all constraints. Write out all .unlock files

        :returns: Generator of ``.unlock`` absolute paths
        :rtype: collections.abc.Generator[pathlib.Path, None, None]
        """
        if is_module_debug:  # pragma: no cover
            msg_info = f"InFiles.write zeroes count: {len(list(self.zeroes))}"
            _logger.info(msg_info)
        else:  # pragma: no cover
            pass

        for in_ in self.zeroes:
            abspath_zero = in_.abspath(self.cwd)
            is_shared_pin = abspath_zero.name.startswith("pins") and is_shared(
                abspath_zero.name
            )
            if not is_shared_pin:
                abspath_unlocked = replace_suffixes_last(abspath_zero, SUFFIX_UNLOCKED)

                if is_module_debug:  # pragma: no cover
                    msg_info = f"InFiles.write abspath_unlocked: {abspath_unlocked}"
                    _logger.info(msg_info)
                else:  # pragma: no cover
                    pass

                abspath_unlocked.touch(mode=0o644, exist_ok=True)
                is_file = abspath_unlocked.exists() and abspath_unlocked.is_file()

                if is_module_debug:  # pragma: no cover
                    msg_info = f"InFiles.write is_file: {is_file}"
                    _logger.info(msg_info)
                else:  # pragma: no cover
                    pass

                if is_file:
                    sep = os.linesep
                    lst_reqs_unsorted = list(in_.requirements)
                    lst_reqs_alphabetical = sorted(lst_reqs_unsorted)
                    contents = sep.join(lst_reqs_alphabetical)
                    contents = f"{contents}{sep}"
                    abspath_unlocked.write_text(contents)
                    yield abspath_unlocked
                else:  # pragma: no cover
                    pass
            else:  # pragma: no cover
                pass

        yield from ()
