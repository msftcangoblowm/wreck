"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

reqs package entrypoint

Commands:

- fix
- unlock

Has pep366 support, without installing the package, can call the
source code, as long has has required dependencies installed

"""

import logging
import logging.config
import os
import sys
import traceback
from pathlib import Path

import click
import strictyaml as s
from logging_strict import (
    LoggingConfigCategory,
    LoggingState,
)
from logging_strict.logging_yaml_validate import validate_yaml_dirty
from logging_strict.register_config import ExtractorLoggingConfig

# pep366 ...
# https://stackoverflow.com/a/34155199
if __name__ == "__main__" and __spec__ is None:  # pragma: no cover
    # Package not installed
    # python src/wreck/cli_dependencies.py fix
    import importlib.util

    path_d = Path(__file__).parent
    rev_mods = []
    while path_d.joinpath("__init__.py").exists():
        name = path_d.name
        path_prev = path_d
        path_d = path_d.parent
        rev_mods.append(name)
    # One level above top package --> sys.path.insert
    sys.path.insert(1, str(path_d))
    # parent (aka package) dotted path
    dotted_path = ".".join(reversed(rev_mods))

    # print(f"str(path_d): {str(path_d)}", file=sys.stderr)
    # print(f"dotted_path: {dotted_path}", file=sys.stderr)
    # print(f"path_prev: {path_prev}", file=sys.stderr)
    pass

    # import top package level
    path_top = path_prev.joinpath("__init__.py")
    spec_top = importlib.util.spec_from_file_location(name, path_top)
    mod_top = importlib.util.module_from_spec(spec_top)
    sys.modules[dotted_path] = mod_top
    spec_top.loader.exec_module(mod_top)

    # __spec__ is None. Set __spec__ rather than :code:`__package__ = dotted_path`
    dotted_path_this = f"{dotted_path}.{Path(__file__).stem}"
    spec_this = importlib.util.spec_from_file_location(dotted_path_this, Path(__file__))
    __spec__ = spec_this
elif (
    __name__ == "__main__" and isinstance(__package__, str) and len(__package__) == 0
):  # pragma: no cover
    # When package is not installed
    # python -m wreck.cli_dependencies {fix,unlock,fix_v1}
    dotted_path = "wreck"
    path_pkg_base_dir = Path(__file__).parent.parent
    sys.path.insert(1, str(path_pkg_base_dir))

    mod = __import__(dotted_path)
    sys.modules[dotted_path] = mod

    __package__ = dotted_path
else:
    # reqs {fix,unlock,fix_v1}
    # __package__ = "wreck"
    pass

# pep366 ...done

from .constants import g_app_name
from .exceptions import MissingRequirementsFoldersFiles
from .lock_collections import unlock_compile
from .lock_compile import (
    is_timeout,
    lock_compile,
)
from .lock_fixing import Fixing
from .pep518_venvs import VenvMapLoader

# Use package logger, not module logger
is_module_debug = True
g_logger_dotted_path = g_app_name
_logger = logging.getLogger(g_logger_dotted_path)

# taken from pyproject.toml
entrypoint_name = "reqs"  # noqa: F401

help_path = "The root directory [default: pyproject.toml directory]"
help_venv_path = "Limit call to one venv. Supply posix style relative path"
help_timeout = "Web connection time out in seconds"
help_is_dry_run = "Do not apply changes, merely report what would have occurred"
help_show_unresolvables = (
    "Show unresolvable dependency conflicts. Needs manual intervention"
)
help_show_fixed = "Show fixed dependency issues"
help_show_resolvable_shared = (
    "Show shared resolvable dependency conflicts. Needs manual intervention"
)
help_verbose = "For main logger, increase logging granularity"

EPILOG_FIX_V2 = """
EXIT CODES

0 -- Evidently sufficient effort put into unittesting. Job well done, beer on me!

1 -- Failures occurred. failed compiles report onto stderr

2 -- entrypoint incorrect usage

3 -- path given for config file reverse search cannot find a pyproject.toml file

4 -- pyproject.toml config file parse issue. Expecting [[tool.wreck.venvs]] sections

5 -- package pip-tools is required to lock package dependencies. Install it

6 -- Missing some .in files. Support file(s) not checked

7 -- venv base folder does not exist. Create it

8 -- expecting [[tool.wreck.venvs]] field reqs to be a sequence

9 -- No such venv found

10 -- timeout occurred. Check web connection

11 -- YAML validation unsuccessful for either registry or logging config YAML file

12 -- venv relpath not provided. Be conscious of venv and python interpreter version

"""

EPILOG_UNLOCK = """
EXIT CODES

0 -- Evidently sufficient effort put into unittesting. Job well done, beer on me!

2 -- entrypoint incorrect usage

3 -- path given for config file reverse search cannot find a pyproject.toml file

4 -- pyproject.toml config file parse issue. Expecting [[tool.wreck.venvs]] sections

6 -- Missing some .in files. Support file(s) not checked

7 -- venv base folder does not exist. Create it

8 -- expecting [[tool.wreck.venvs]] field reqs to be a sequence

9 -- No such venv found

"""


def present_results(
    fcn,
    venv_relpath,
    lock_msgs_for_venv,
    lock_unresolvables_for_venv,
    lock_applies_to_shared_for_venv,
    unlock_msgs_for_venv,
    unlock_applies_to_shared_for_venv,
    show_unresolvables,
    show_fixed,
    show_resolvable_shared,
):
    """Present results groups by venv."""
    dotted_path = f"{g_app_name}.cli_dependencies.present_results"
    lock_resolved_msgs_count = len(lock_msgs_for_venv)
    lock_unresolvables_count = len(lock_unresolvables_for_venv)
    lock_applies_to_shared_count = len(lock_applies_to_shared_for_venv)

    unlock_resolved_msgs_count = len(unlock_msgs_for_venv)
    unlock_applies_to_shared_count = len(unlock_applies_to_shared_for_venv)

    # summary header
    msg_info = (
        f"{dotted_path} lock_unresolvables_count {lock_unresolvables_count} "
        f"{show_unresolvables}{os.linesep}"
        f"lock_applies_to_shared_count {lock_applies_to_shared_count} "
        f"{show_resolvable_shared}{os.linesep}"
        f"lock_resolved_msgs_count {lock_resolved_msgs_count} "
        f"{show_fixed}{os.linesep}"
        f"unlock_resolved_msgs_count {unlock_resolved_msgs_count}{os.linesep}"
        f"unlock_applies_to_shared_count {unlock_applies_to_shared_count}{os.linesep}"
    )
    _logger.info(msg_info)

    # lock messages
    is_show = lock_unresolvables_count != 0 and show_unresolvables
    if is_show:  # pragma: no cover
        zzz_unresolvables = f"Unresolvables ({venv_relpath}){os.linesep}"
        for blob in lock_unresolvables_for_venv:
            zzz_unresolvables += f"{blob!r}{os.linesep}"
        fcn(zzz_unresolvables, err=True)
    else:  # pragma: no cover
        pass

    is_show = lock_applies_to_shared_count != 0 and show_resolvable_shared
    if is_show:  # pragma: no cover
        zzz_resolvables_shared = (
            f".shared resolvable (manually {venv_relpath}):" f"{os.linesep}{os.linesep}"
        )
        for blob in lock_applies_to_shared_for_venv:
            zzz_resolvables_shared += f"{blob!r}{os.linesep}"
        fcn(zzz_resolvables_shared, err=True)
    else:  # pragma: no cover
        pass

    is_show = lock_resolved_msgs_count != 0 and show_fixed
    if is_show:  # pragma: no cover
        zzz_fixed = f"Fixed ({venv_relpath}):{os.linesep}{os.linesep}"
        for blob in lock_msgs_for_venv:
            zzz_fixed += f"{blob!r}{os.linesep}"
        fcn(zzz_fixed, err=True)
    else:  # pragma: no cover
        pass

    # unlock messages
    is_show = unlock_applies_to_shared_count != 0 and show_resolvable_shared
    if is_show:  # pragma: no cover
        zzz_resolvables_shared = (
            f".shared resolvable (manually {venv_relpath}):" f"{os.linesep}{os.linesep}"
        )
        for blob in unlock_applies_to_shared_for_venv:
            zzz_resolvables_shared += f"{blob!r}{os.linesep}"
        fcn(zzz_resolvables_shared, err=True)
    else:  # pragma: no cover
        pass

    is_show = unlock_resolved_msgs_count != 0 and show_fixed
    if is_show:  # pragma: no cover
        zzz_fixed = f"Fixed ({venv_relpath}):{os.linesep}{os.linesep}"
        for blob in unlock_msgs_for_venv:
            zzz_fixed += f"{blob!r}{os.linesep}"
        fcn(zzz_fixed, err=True)
    else:  # pragma: no cover
        pass


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
)
def main():
    """Command-line for reqs. Prints usage"""


@main.command(
    "fix",
    context_settings={"ignore_unknown_options": True},
    epilog=EPILOG_FIX_V2,
)
@click.option(
    "-p",
    "--path",
    default=Path.cwd(),
    type=click.Path(
        exists=False,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        path_type=Path,
    ),
    help=help_path,
)
@click.option(
    "-v",
    "--venv-relpath",
    default=None,
    help=help_venv_path,
)
@click.option(
    "-t",
    "--timeout",
    default=15,
    type=click.INT,
    help=help_timeout,
)
@click.option(
    "--show-unresolvables / --hide-unresolvables",
    "show_unresolvables",
    default=True,
    help=help_show_unresolvables,
    is_flag=True,
)
@click.option(
    "--show-fixed / --hide-fixed",
    "show_fixed",
    default=True,
    help=help_show_fixed,
    is_flag=True,
)
@click.option(
    "--show-resolvable-shared / --hide-resolvable-shared",
    "show_resolvable_shared",
    default=True,
    help=help_show_resolvable_shared,
    is_flag=True,
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help=help_verbose,
)
def requirements_fix_v2(
    path,
    venv_relpath,
    timeout,
    show_unresolvables,
    show_fixed,
    show_resolvable_shared,
    verbose,
):
    """Lock dependencies creates (``*.lock``) files

    Disadvantages of locking dependencies

    1. FOSS is ``as-is``, largely unpaid work, often lacks necessary
       skillset, often doesn't care to do tedious tasks, is pressed for
       time, and live happens. These are the people supposed to be
       making packages for production use?! Having such expectations
       is ridiculous and conflicts with the human condition

    2. package quickly becomes unusable when, not if, the author is no longer
       maintaining the package

    3. Non-experts might not be using pipenv, only pip. Almost guaranteeing
       dependency hell. ``pip`` won't have what it needs to resolve
       dependency version conflicts

    4. ``pipenv`` says don't automate updating dependency lock files thru CI/CD

    5. Multiple calls to ``pip-compile`` **always** causes avoidable mistakes;
       choosing non-sync'ed dependency versions.

    Advantage

    1. Job security. Knowledgable eyeballs **must** regularly update
       dependency version locks

    2. ``pipenv`` discourages attackers setting up alternative repository hosts
       ``pypi.org`` and swapping out an obscure package with their own.

    3. The stars align in the cosmos, miraculously, all package authors regularly
       update their packages dependencies' locks. Get that warm feeling inside
       knowing we are alive, loved, and appreciated. We shout,
       ``it's a miracle!`` and be right!

    Usage

    reqs fix

    or

    python src/wreck/cli_dependencies.py fix

    \f

    :param path:

       The root directory [default: pyproject.toml directory]

    :type path: pathlib.Path
    :param venv_relpath: Filter by venv relative path
    :type venv_relpath: pathlib.Path
    :param timeout: Default 15. Web connection time out in seconds
    :type timeout: int
    :param show_unresolvables: Default True. Report unresolvable dependency conflicts
    :type show_unresolvables: bool
    :param show_fixed: Default True. Report fixed issues
    :type show_fixed: bool
    :param show_resolvable_shared:

       Default True. Report resolvable issues affecting ``.shared.{.unlock, .lock}``
       files.

    :type show_resolvable_shared: bool
    """
    global _logger
    str_path = path.as_posix()
    dotted_path = f"{g_app_name}.cli_dependencies.dependencies_lock"
    fcn = click.secho

    # Running all venv with the same python interpreter is a bad idea
    # lock_compile allows, but Fixing.fix_requirements_lock and present_results does not
    if venv_relpath is None:
        msg_warn = (
            "venv relpath not provided. Be conscious of venv and python "
            "interpreter version"
        )
        fcn(msg_warn, fg="red", err=True)
        sys.exit(12)
    else:
        # venv relpath provided ... continue
        pass

    _genre = "mp"
    _flavor = "asz"
    #    may raise strictyaml.YAMLValidationError
    if LoggingState().is_state_app:  # pragma: no cover
        """loading app logging config without having dependency installed
        would cause side effect --> ImportError"""
        cat = LoggingConfigCategory.UI
    else:
        # normal case
        cat = LoggingConfigCategory.WORKER
    elc = ExtractorLoggingConfig(g_app_name)
    try:
        # may raise strictyaml.YAMLValidationError
        elc.get_db()

        elc.query_db(
            cat,
            genre=_genre,
            flavor=_flavor,
            logger_package_name=g_app_name,
        )

        if elc.logging_config_yaml_str is not None:
            # may raise strictyaml.YAMLValidationError
            yaml_config = validate_yaml_dirty(elc.logging_config_yaml_str)
            d_config = yaml_config.data
            # In tests, to skip applying logging config, patch this
            logging.config.dictConfig(d_config)
        else:  # pragma: no cover
            pass
    except s.YAMLValidationError as exc:
        fcn(str(exc), fg="red", err=True)
        sys.exit(11)

    is_increase_logging_verbosity = verbose > 0
    if is_increase_logging_verbosity:
        """Take logging level from package (not set for module).
        To reduce side effects surface area, alter logger for module, not package
        """
        # logger_mod_this = logging.getLogger(g_logger_dotted_path)
        log_level = max(logging.DEBUG, _logger.level - verbose * 10)
        _logger.setLevel(log_level)
    else:
        pass

    try:
        loader = VenvMapLoader(str_path)
    except FileNotFoundError:
        # Couldn't find the pyproject.toml file
        msg_exc = (
            f"Reverse search lookup from {path!r} could not "
            f"find a pyproject.toml file. {traceback.format_exc()}"
        )
        # raise click.ClickException(msg_exc)
        fcn(msg_exc, fg="red", err=True)
        sys.exit(3)
    except LookupError:
        msg_exc = (
            "In pyproject.toml, expecting sections [[tool.wreck.venvs]]. Create them"
        )
        fcn(msg_exc, fg="red", err=True)
        sys.exit(4)

    if is_module_debug:  # pragma: no cover
        msg_info = f"{dotted_path} loader.project_base {loader.project_base}"
        _logger.info(msg_info)
    else:  # pragma: no cover
        pass

    # compile .lock files
    try:
        t_status = lock_compile(loader, venv_relpath, timeout)
    except (MissingRequirementsFoldersFiles, AssertionError) as exc:
        # Careful MissingRequirementsFoldersFiles is a subclass of AssertionError
        # Missing ``.in`` files. Support file(s) not checked
        if isinstance(exc, MissingRequirementsFoldersFiles):
            fcn(str(exc), fg="red", err=True)
            sys.exit(6)
        else:
            msg_exc = (
                "pip-tools is required to lock package dependencies. Install "
                f"it. {traceback.format_exc()}"
            )
            # raise click.ClickException(msg_exc)
            fcn(msg_exc, fg="red", err=True)
            sys.exit(5)
    except NotADirectoryError as exc:
        # venv folder needs to exist
        fcn(str(exc), fg="red", err=True)
        sys.exit(7)
    except ValueError as exc:
        # expecting ``[[tool.wreck.venvs]]`` field reqs to be a sequence
        fcn(str(exc), fg="red", err=True)
        sys.exit(8)
    except KeyError as exc:
        # No such venv found
        fcn(str(exc), fg="red", err=True)
        sys.exit(9)

    is_tuple_two_items = (
        t_status is not None and isinstance(t_status, tuple) and len(t_status) == 2
    )
    assert is_tuple_two_items
    t_compiled, t_failures = t_status
    assert isinstance(t_failures, tuple)
    assert isinstance(t_compiled, tuple)
    if is_timeout(t_failures):
        fcn("Timeout occurred. Check web connection", err=True)
        sys.exit(10)
    else:
        is_failures = len(t_failures) != 0
        if is_failures:
            """To cause a failure, an ``.in`` would have to: be
            wrong file format or contain invalid entries"""
            fcn(f"failures {t_failures}", err=True)
            sys.exit(1)
        else:  # pragma: no cover
            # 2nd pass. Fixes locked, creates unlock, fixes unlock
            try:
                fixing = Fixing.fix_requirements_lock(loader, venv_relpath)
            except MissingRequirementsFoldersFiles as exc:
                fcn(str(exc), fg="red", err=True)
                sys.exit(6)

            """Present results.

            Only deals with one venv at a time cuz environments and venv
            required python interpreter version could and most likely will differ
            """
            lock_msgs_for_venv = fixing._out_lock_messages.fixed_issues
            lock_unresolvables_for_venv = fixing._out_lock_messages.unresolvables
            lock_applies_to_shared_for_venv = (
                fixing._out_lock_messages.resolvable_shared
            )
            unlock_msgs_for_venv = fixing._out_unlock_messages.fixed_issues
            unlock_applies_to_shared_for_venv = (
                fixing._out_unlock_messages.resolvable_shared
            )

            present_results(
                fcn,
                venv_relpath,
                lock_msgs_for_venv,
                lock_unresolvables_for_venv,
                lock_applies_to_shared_for_venv,
                unlock_msgs_for_venv,
                unlock_applies_to_shared_for_venv,
                show_unresolvables,
                show_fixed,
                show_resolvable_shared,
            )

            sys.exit(0)


@main.command(
    "unlock",
    context_settings={"ignore_unknown_options": True},
    epilog=EPILOG_UNLOCK,
    deprecated=True,
    hidden=True,
)
@click.option(
    "-p",
    "--path",
    default=Path.cwd(),
    type=click.Path(
        exists=False,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        path_type=Path,
    ),
    help=help_path,
)
@click.option(
    "-v",
    "--venv-relpath",
    default=None,
    help=help_venv_path,
)
def requirements_unlock(path, venv_relpath):
    """Unlock dependencies creates (``*.unlock``) files

    Package dependencies are only locked if the package is an app.
    A ``.in`` resolves ``-r`` and ``-c``, which can be understood by pip

    Usage

    reqs unlock

    or

    python src/wreck/cli_dependencies.py unlock

    \f

    :param path:

       The root directory [default: pyproject.toml directory]

    :type path: pathlib.Path
    :param venv_relpath: Filter by venv relative path
    :type venv_relpath: pathlib.Path
    """
    str_path = path.as_posix()

    try:
        loader = VenvMapLoader(str_path)
    except FileNotFoundError:
        # Couldn't find the pyproject.toml file
        msg_exc = (
            f"Reverse search lookup from {path!r} could not "
            f"find a pyproject.toml file. {traceback.format_exc()}"
        )
        # raise click.ClickException(msg_exc)
        click.secho(msg_exc, fg="red", err=True)
        sys.exit(3)
    except LookupError:
        msg_exc = (
            "In pyproject.toml, expecting sections [[tool.wreck.venvs]]. Create them"
        )
        click.secho(msg_exc, fg="red", err=True)
        sys.exit(4)

    # resolve ``.in`` --> ``.unlock`` files
    gen = unlock_compile(loader, venv_relpath)
    try:
        lst = list(gen)  # execute generator
    except MissingRequirementsFoldersFiles as exc:
        # Missing ``.in`` files. Support file(s) not checked
        click.secho(str(exc), fg="red", err=True)
        sys.exit(6)
    except NotADirectoryError as exc:
        # venv folder needs to exist
        click.secho(str(exc), fg="red", err=True)
        sys.exit(7)
    except ValueError as exc:
        # expecting ``[[tool.wreck.venvs]]`` field reqs to be a sequence
        click.secho(str(exc), fg="red", err=True)
        sys.exit(8)
    except KeyError as exc:
        # No such venv found
        click.secho(str(exc), fg="red", err=True)
        sys.exit(9)
    else:
        click.secho(f"created {lst!s}", err=True)
        sys.exit(0)


if __name__ == "__main__":  # pragma: no cover
    main()
