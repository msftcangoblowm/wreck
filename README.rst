Wreck
======

From .in requirement files generate and fix .lock and .unlock files

|  |kit| |codecov| |license|
|  |last-commit| |test-status| |quality-status| |docs|
|  |versions| |implementations|
|  |platforms| |black|
|  |downloads| |stars|
|  |mastodon-msftcangoblowm|

|feature banner|

.. PYVERSIONS

\* Python 3.9 through 3.13, PyPy

**new in 0.3.x**

pyproject.toml tool.wreck section; tool.wreck.create_pins_unlock config option;
remove .in file handling legacy implementation (\#17);
warn .in includes .lock (\#23); remove setuptools and pip in .lock (\#35);
cower and pay homage to pypi.org cartel (\#30);

**new in 0.2.x**

compatible release operator support; arbitrary equality issue UnResolvable;
add logging-strict and pytest-logging-strict support;

What wreck?
------------

**Fix the requirements/constraint files and there would be little or no need to fix venvs**

``wreck`` is a homophone (same or similar pronunciation) of req,
abbreviated form of requirement. The past tense of wreck is either
wrecked or rekt; depending on how old you are.

Generates both lock and unlock requirement files. Fixes both!
Minimizing the likelihood of dependency conflicts

Focus is on the requirements and constraints files, venv aware, but not
dependent on venv. Not a venv manager.

Caters to authors of apps (lock) and packages (lock and unlock).

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

Configuration
--------------

In pyproject.toml, for each venv, add a ``[[tool.venv]]`` section.

.. code:: text

   [[tool.wreck.venvs]]
   venv_base_path = '.venv'
   reqs = [
       'requirements/dev',
       'requirements/kit',
       'requirements/pip',
       'requirements/pip-tools',
       'requirements/prod.shared',
       'requirements/manage',
       'requirements/mypy',
       'requirements/tox',
   ]

   [[tool.wreck.venvs]]
   venv_base_path = '.doc/.venv'
   reqs = [
       'docs/requirements',
       'docs/pip-tools',
   ]

These are top most level requirement files without last suffix.

The additional requirements are for use by tox and CI/CD workflows.

- use posix relative paths

- assumed the venv are within the package base folder

- requirements and constraints files are not required to be in a subfolder,
  however it's highly encouraged

package author
"""""""""""""""

Possible corresponding dependency section

.. code:: text

   [tool.setuptools.dynamic]

   dependencies = { file = ['requirements/prod.shared.unlock'] }
   optional-dependencies.pip = { file = ['requirements/pip.lock'] }
   optional-dependencies.pip_tools = { file = ['requirements/pip-tools.lock'] }
   optional-dependencies.dev = { file = ['requirements/dev.lock'] }
   optional-dependencies.manage = { file = ['requirements/manage.lock'] }
   optional-dependencies.docs = { file = ['docs/requirements.lock'] }

Dependencies last suffix is ``.unlock``

apps author
""""""""""""

Possible corresponding dependency section

.. code:: text

   [tool.setuptools.dynamic]
   dependencies = { file = ['requirements/prod.shared.lock'] }
   optional-dependencies.pip = { file = ['requirements/pip.lock'] }
   optional-dependencies.pip_tools = { file = ['requirements/pip-tools.lock'] }
   optional-dependencies.dev = { file = ['requirements/dev.lock'] }
   optional-dependencies.manage = { file = ['requirements/manage.lock'] }
   optional-dependencies.docs = { file = ['docs/requirements.lock'] }

Dependencies last suffix is ``.lock``

Usage
------

.. code:: shell

   req fix --venv-relpath='.venv'
   req fix --venv-relpath='.doc/.venv'

Provide path to the ``pyproject.toml`` if different location from cwd.
Either the absolute path to the base folder or the file.

.. code:: shell

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

wreck theory
"""""""""""""

The ``requirements-`` prefix is noisy, provides no useful info, ugly.
It's use is discouraged.

.. csv-table:: files
   :header: file, description
   :widths: auto

   "\*.in", "raw requirement or constraints file"
   "\*.shared.in", "constraints file could be shared by more than one venv"
   "\*.lock", "locked requirement file"
   "\*.unlock", "unlocked requirement file"

There is also ``*.shared.lock`` and ``*.shared.unlock``

Document issues in the respective ``*.in`` and ``*.shared.in`` file. Every
undocumented pin is bad UX.

The fixes of each dependency conflict issue should be separated into
a ``pins-*[.shared].in`` file.

e.g. ``pins-ccfi.in`` or ``pins-myst-parser.in``

When the crisis is over. Removed these files along with any links to them.

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

License
--------

``aGPLv3+``

The short ramifications are:

- commercial/public entities must obtain a license waiver

Meaning pay to support the project and towards funding ongoing package maintenance.

- Do not change the copyright notice; that's serious IP theft.

.. |last-commit| image:: https://img.shields.io/github/last-commit/msftcangoblowm/wreck/master
    :target: https://github.com/msftcangoblowm/wreck/pulse
    :alt: last commit to gauge activity
.. |test-status| image:: https://github.com/msftcangoblowm/wreck/actions/workflows/testsuite.yml/badge.svg?branch=master&event=push
    :target: https://github.com/msftcangoblowm/wreck/actions/workflows/testsuite.yml
    :alt: Test suite status
.. |quality-status| image:: https://github.com/msftcangoblowm/wreck/actions/workflows/quality.yml/badge.svg?branch=master&event=push
    :target: https://github.com/msftcangoblowm/wreck/actions/workflows/quality.yml
    :alt: Quality check status
.. |docs| image:: https://readthedocs.org/projects/wreck/badge/?version=latest&style=flat
    :target: https://wreck.readthedocs.io/
    :alt: Documentation
.. |kit| image:: https://img.shields.io/pypi/v/wreck
    :target: https://pypi.org/project/wreck/
    :alt: PyPI status
.. |versions| image:: https://img.shields.io/pypi/pyversions/wreck.svg?logo=python&logoColor=FBE072
    :target: https://pypi.org/project/wreck/
    :alt: Python versions supported
.. |license| image:: https://img.shields.io/github/license/msftcangoblowm/wreck
    :target: https://pypi.org/project/wreck/blob/master/LICENSE
    :alt: License
.. |stars| image:: https://img.shields.io/github/stars/msftcangoblowm/wreck.svg?logo=github
    :target: https://github.com/msftcangoblowm/wreck/stargazers
    :alt: GitHub stars
.. |mastodon-msftcangoblowm| image:: https://img.shields.io/mastodon/follow/112019041247183249
    :target: https://mastodon.social/@msftcangoblowme
    :alt: msftcangoblowme on Mastodon
.. |codecov| image:: https://codecov.io/gh/msftcangoblowm/wreck/branch/master/graph/badge.svg?token=VZAM1geSFh
    :target: https://codecov.io/gh/msftcangoblowm/wreck
    :alt: wreck coverage percentage
.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/ambv/black
.. |downloads| image:: https://img.shields.io/pypi/dm/wreck
.. |implementations| image:: https://img.shields.io/pypi/implementation/wreck
.. |platforms| image:: https://img.shields.io/badge/platform-linux-lightgrey

.. https://img.shields.io/badge/platform-windows%20%7C%20macos%20%7C%20linux-lightgrey

.. |feature banner| image:: /docs/_static/wreck-banner-611-255-1.svg
   :alt: fixes python package requirement files
