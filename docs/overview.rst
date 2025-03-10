.. raw:: html

   <div style="visibility: hidden; display: none;">

Overview
=========

.. raw:: html

   </div>

Create and fix ``.lock``. Using know-how just gleened, fix ``.unlock``

What wreck means?
------------------

``wreck`` is a homophone (same or similar pronunciation) of req,
abbreviated form of requirement. The past tense of wreck is either
wrecked or rekt; depending on how old you are.

What wreck does
----------------

|feature banner|

Dev tool for authors of Python apps (lock) and packages (lock and unlock).

Generates both lock and unlock requirement files. Fixes both!

Not automagically resolved

- unresolvable dependency conflicts are

- .in files shared by >1 venv

.. epigraph::

   Fix the requirements/constraint files and there would be little or no need to fix venvs

In one command, fix requirements for one venv

Focus is on the requirements and constraints files, venv aware, but not
dependent on venv.

Wreck is not
-------------

- Not a venv manager

- Not a build backend

Recommended habits
-------------------

- requirements files are placed in subfolder(s), not pyproject.toml

- requirements are grouped by venv relative path

- ``requirements-`` prefix is noisy, provides no useful info, ugly.
  It's use is discouraged.

Gauge the demand
-----------------

Frustrating
""""""""""""

GIL and multithreading UX aside, resolving dependency conflicts is the next
most frustrating issue facing Python coders

multiple venv
""""""""""""""

Often don't consider there will be multiple venv, not always just one.
So all requirements don't apply to all venv

Easy learning curve
""""""""""""""""""""

Configuration read from pyproject.toml. There is one section per venv. Then
run one cli command per venv.

Unlike other packages, per .in file, produces two files: .unlock and .lock

For a particular venv, **fixes all** requirement files, rather than one
file at a time

app and package authors
""""""""""""""""""""""""

The needs of an app and a package author cannot be solved by a tool
that caters only towards app authors

New suffixes
-------------

- ``requirements-*.txt`` files have both compiled and rendered (``.unlock``) variants

- compile (``.lock``) and rendered (``.unlock``) are both needed

- constraint files are either shared across more than one venv or not

.. csv-table:: files
   :header: file, description
   :widths: auto

   "\*.in", "raw requirement or constraints file"
   "\*.shared.in", "constraints file shared by more than one venv"
   "\*[.shared].lock", "locked requirement file"
   "\*[.shared].unlock", "unlocked requirement file"

Document issues in the respective ``*.in`` and ``*.shared.in`` file. Every
undocumented pin is bad UX.

The fixes of each dependency conflict issue should be separated into
a ``pins-*[.shared].in`` file.

e.g. ``pins-ccfi.in`` or ``pins-myst-parser.in``

When the crisis is over. Removed these files along with any links to them.

Not automatically resolved
---------------------------

For dependency conflicts, that can't be automagically resolved,
falls into these categories:

- unresolvable

   ``pip<24.2`` and ``pip>=24.2`` is unresolvable.

   One possible solution is to split requirements into multiple venv

- shared between multiple venv

   Ideally, code is kept DRY (don't repeat yourself) as pragmatic. This
   applies equally to requirements and constraints.

   ``.shared.in`` constraints are included into many venv, special care
   must be taken.

   ``wreck`` deals with fixing requirements and constraints which apply
   to one venv at a time. When applies to multiple venv, ``wreck`` supports
   this, but can't fix conflicts.

Usage
------

:doc:`install and config <getting_started/installation>`

.. code-block:: shell

   req fix --venv-relpath='.venv'
   cd .tox && tox -r --root=.. -c ../tox-req.ini -e docs --workdir=.; cd - &>/dev/null

The later calls :code:`req fix --venv-relpath='.doc/.venv'` in venv with py310

Provide path to the ``pyproject.toml`` if different location from cwd.
Either the absolute path to the base folder or the file.

.. code-block:: shell

   req fix --venv-relpath='.venv' --path=~/parent_folder/package_base_folder
   req fix --venv-relpath='.venv' --path=~/parent_folder/package_base_folder/pyproject.toml

``--venv-relpath`` does not support absolute path

Command options
""""""""""""""""

.. csv-table:: :code:`reqs fix` options
   :header: cli, default, description
   :widths: auto

   "-p/--path", "cwd", "absolute path to package base folder"
   "-v/--venv-relpath", "None", "venv relative path. None implies all venv use the same python interpreter version"
   "-t/--timeout", "15", "Web connection time in seconds"
   "--show-unresolvables", "True", "For each venv, in a table print the unresolvable dependency conflicts"
   "--show-fixed", "True", "For each venv, in a table print fixed issues"
   "--show-resolvable-shared", "True", "For each venv in a table print resolvable issues that involve .shared.in files"

Exit codes
"""""""""""

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

Theory
-------

Current theory
"""""""""""""""

.. csv-table:: files
   :header: file, description
   :widths: auto

   "requirements-\*.in", "might contain pins. Maybe either a requirement or a constraints file"
   "requirements-\*.txt", "output file consumable by pip"

Difference between requirements and constraints

- constraints files cannot have lines with ``-e``
- constraints files cannot have lines with  extras e.g. ``coverage[toml]``
- If needed, constraints are applied

Market research
----------------

.. csv-table:: packages
   :header: package, description
   :widths: auto

   "pip-compile-multi", "sync multiple calls produces lock files"
   "uv", "A venv manager. Offers cli options to resolve conflicts"
   "poetry", "venv manager and build backend. Complex config within pyproject.toml"

.. csv-table:: base packages
   :header: package, description
   :widths: auto

   "pip-tools", "does not sync multiple calls"
   "pip", "present actionable info. Includes an ugly traceback"

.. csv-table:: not useful
   :header: package, description
   :widths: auto

   "pyp2req", "| venv unaware. Fixes nothing.
   | Prints backend requires and top level dependencies to stdout"

No package deals exclusively, effectively, and solely with requirements/constraint
files. The top packages, which actual fixes dependency conflicts, are
venv managers. Gives options to mitigate issues.

The top packages apply fixes to the venv, not the requirements/constraint files.

**If the requirements/constraint files are fixed, there would be little or no need to fix venvs.**

If anyone disagrees with these assessments of other packages, create
an issue. Recommend a 1-2 line description

Known issues
-------------

Any/all known shortcomings are tracked within ``CHANGES.rst`` section
``Known regressions``.

Accepted feature requests are tracked within ``CHANGES.rst`` section ``Feature request``.
There should also be a corresponding issue.

Contributing advice
--------------------

See :doc:`contributing`

License
--------

``aGPLv3+``

The short ramifications are:

- commercial/public entities must obtain a license waiver

Meaning pay to support the project and towards funding ongoing package maintenance.

- Do not change the copyright notice; that's serious IP theft.

.. |feature banner| image:: _static/wreck-banner-611-255-1.*
   :alt: wreck fixes Python pip requirements files
