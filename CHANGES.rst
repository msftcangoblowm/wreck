.. this will be appended to README.rst

Changelog
=========

..

   Feature request
   .................

   - Review everywhere a subprocess occurs. Sanitize user input.
     e.g. --venv-relpath should only contain alphanumeric hyphen underscore forwardslash
     https://github.com/ultralytics/ultralytics/issues/18027#issuecomment-2521308429
     https://matklad.github.io/2021/07/30/shell-injection.html

   - remove module wreck.lock_infile and support via functools.singledispatch

   Known regressions
   ..................

   - add support for package url

   Commit items for NEXT VERSION
   ..............................

.. scriv-start-here

.. _changes_0-2-0:

Version 0.2.0 — 2024-12-08
--------------------------

- docs: fix some in-code links to use intersphinx
- feat: add support for compatiable release operator (#6)
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
