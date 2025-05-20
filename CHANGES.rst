.. this will be appended to README.rst

Changelog
=========

..

   Feature request
   .................

   - add support for package url

   - release-drafter creating release notes on commit rather than on release

   - Review everywhere a subprocess occurs. Sanitize user input.
     e.g. --venv-relpath should only contain alphanumeric hyphen underscore forwardslash
     https://github.com/ultralytics/ultralytics/issues/18027#issuecomment-2521308429
     https://matklad.github.io/2021/07/30/shell-injection.html

   - remove module wreck.lock_infile and support via functools.singledispatch

   - reqs fix
     Skip write if file has same sha512 signature

   - tox-req.ini has two targets: base and docs. lock+fix of prod.shared.lock
     gets different results. The difference only affects presence/absence
     of a comment. target docs is unaware of setuptools-scm.

     For target docs, do not save prod.shared.lock?
     Add option, ``--skip-write='[requirements relpath]'``
     Allow option usage multiple times
     Skip these:
     requirements/pins-cffi.unlock
     requirements/prod.shared.lock

   Known regressions
   ..................

   - in pyproject.toml of [tools.piptools] section will interfere with wreck
     hashes not supported and findlinks not supported

   - venv missing folder(s). pep518_venvs.py --> NotADirectoryError

     ensure ``.doc/.venv`` does not exist. Then call

     reqs fix --path=/mnt/sda1/dev_parent/decimals --venv-relpath='.venv'

     Not caught Exception results in nasty traceback.

     All venv base folder(s) must exist. Missing folder
     PosixPath('/mnt/sda1/dev_parent/decimals/.doc/.venv'). Create it

     Should report in one line, not the uncaught traceback

   - During ``.in`` load process, line with unknown operator (e.g. ``~~``)
     is silently ignored (#7)

   - venv_path is assumed to be a relative path. What if it's outside of the
     package folder tree? Then assumption relative to package base folder
     becomes incorrect

   Commit items for NEXT VERSION
   ..............................

.. scriv-start-here

.. _changes_0-3-5:

Version 0.3.5 — 2025-05-20
--------------------------

- docs: use py313+ avoid ruamel.yaml clib package
- chore: bump versions
- ci: bump versions

.. _changes_0-3-4:

Version 0.3.4 — 2025-04-10
--------------------------

- chore: pep639 compliance
- tests: use logging_strict_tech_niques.get_locals_dynamic remove get_locals
- fix: do not allow unsafe dependencies (#35)
- fix: do not emit build front end options (#30)
- ci: bump gh actions version
- chore: bump logging-strict pytest-logging-strict mypy types-setuptools
- fix: remove dependency setuptools from requirement files

.. _changes_0-3-3:

Version 0.3.3 — 2025-03-10
--------------------------

- tests(test_lock_compile): remove lines with only posix line separator
- ci: bump versions
- tests(test_lock_compile): ~/.pip/pip.conf affects pip-compile output
- chore(pre-commit): yaml formatting auto fix
- chore(pre-commit): typos auto fix

.. _changes_0-3-2:

Version 0.3.2 — 2025-02-07
--------------------------

- feat: warn .in include .lock (#23)
- feat: .lock and .unlock out messages
- chore: update pre-commit. add Makefile target
- chore: pep639 compliance. delayed setuptools#4759
- ci: bump dependencies version

.. _changes_0-3-1:

Version 0.3.1 — 2025-02-01
--------------------------

- remove .in file handling legacy implementation (#17)

.. _changes_0-3-0:

Version 0.3.0 — 2025-01-31
--------------------------

- refactor(MANIFEST.in): categorize what to include into tarball
- refactor(Makefile): separate GNU Make standard targets
- fix: for reqs fix if yaml validation errors exit code 11
- fix: tool.venvs normalize to tool.wreck.venvs
- feat: add config section tool.wreck
- feat: add config option tool.wreck.create_pins_unlock default true (#16)
- feat: add reqs fix --verbose option
- refactor(cli_dependencies): use logging strict registry API
- fix: ensure .unlock have no duplicate lines (#15)
- tests: fix tests after introduce additional dependency file
- fix(requirements): add nudge pin for package virtualenv to mitigate CVE-2024-53899
- fix(tox): rm dir build/lib/ before tox. coverage report avoid remnants
- ci: separate rst2html5 and Sphinx jobs
- tox: separate venv and target for rst2html5 and Sphinx

.. _changes_0-2-4:

Version 0.2.4 — 2025-01-05
--------------------------

- refactor(cli_dependencies): add logging-strict support (#14)
- tests: use pytest fixture logging_strict from package pytest-logging-strict (#14)
- refactor: add dependency logging-strict
- refactor(dev.in): add dependency pytest-logging-strict
- refactor: remove hard coded logging config dict from wreck.constants.LOGGING (#14)
- ci: bump action versions

.. _changes_0-2-3:

Version 0.2.3 — 2024-12-15
--------------------------

- fix: pyproject.toml section pipenv-unlock (#10)

.. _changes_0-2-2:

Version 0.2.2 — 2024-12-14
--------------------------

- fix(pep518_venvs): venv with no reqs (#9)

.. _changes_0-2-1:

Version 0.2.1 — 2024-12-10
--------------------------

- fix(pep518_venvs): missing requirements warning message provide hint
- fix(tox-req.ini): into allowlist_externals add entrypoint reqs
- fix(lock_discrepancy): extract_full_package_name known operators later regex (#7)
- test(lock_fixing): add test case for arbitrary equality

.. _changes_0-2-0:

Version 0.2.0 — 2024-12-08
--------------------------

- docs: fix some in-code links to use intersphinx
- feat: add support for compatible release operator (#6)
- fix(lock_discrepancy): catch invalid SpecifierSet early. Fcn get_ss_set separated out
- refactor: move fcn pprint_pins to module lock_datum
- docs: remove mentions to nonexistent module wreck.lock_inspect
- docs: sync README.rst and docs/overview.rst
- ci: add release drafter gh workflow
- ci: add issue and PR templates

.. _changes_0-1-0:

Version 0.1.0 — 2024-12-06
--------------------------

- fix: fix Windows test issues
- chore: bump gh workflow dependencies
- fix(testsuite): rename requirement prod.shared.unlock to prod.unlock
- test: each test folder descriptive and test for one thing
- docs: add logo favicon and banner
- fix: remove drain-swamp dependencies
- chore: fork from drain-swamp

.. scriv-end-here
