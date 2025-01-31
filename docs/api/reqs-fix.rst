reqs fix
=========

From .in files, creates .lock, .unlock files and fix both.

In ``pyproject.toml``, references ``[[tool.wreck.venvs]]`` sections one for each venv

- Syncs multiple runs of :command:`pip-compile`

- Not exclusive tool for app package authors. ``.unlock`` files are for package authors

Normal usage
-------------

.. code-block:: shell

   reqs fix --venv-relpath='.venv'

If the python interpreter version is not the same, use tox

.. code-block:: shell

   cd .tox && tox -r --root=.. -c ../tox-req.ini -e docs --workdir=.; cd - &>/dev/null

To setup tox see :doc:`../contributing`


Example results
-----------------

Creates the ``.lock``, ``.unlock`` files and fixes both. Run one venv at a time.
When not all venv use the same Python interpreter version, recommend to use tox or nox.

And voila!

Excerpt from ``pyproject.toml``

.. code-block:: text

   [tool.setuptools.dynamic]
   dependencies = { file = ["requirements/prod.unlock"] }
   optional-dependencies.pip = { file = ["requirements/pip.lock"] }
   optional-dependencies.pip_tools = { file = ["requirements/pip-tools.lock"] }
   optional-dependencies.ui = { file = ["requirements/ui.lock"] }
   optional-dependencies.test = { file = ["requirements/test.lock"] }
   optional-dependencies.dev = { file = ["requirements/dev.lock"] }
   optional-dependencies.manage = { file = ["requirements/manage.lock"] }
   optional-dependencies.docs = { file = ["docs/requirements.lock"] }

   version = {attr = "[your package]._version.__version__"}

   [[tool.wreck.venvs]]
   venv_base_path = '.venv'
   reqs = [
       'requirements/dev',
       'requirements/kit',
       'requirements/pip',
       'requirements/pip-tools',
       'requirements/prod',
       'requirements/manage',
       'requirements/mypy',
       'requirements/tox',
   ]

   [[tool.wreck.venvs]]
   venv_base_path = '.doc/.venv'
   reqs = [
       'docs/requirements',
       'docs/pip-tools',
       'requirements/prod',
   ]

Without suffixes. Specific suffixes removed: ``.in`` and ``.shared.in``

Exit codes
-----------

0 -- Evidently sufficient effort put into unittesting. Job well done, beer on me!

1 -- Unused. Reason: too generic

2 -- Path not a folder

3 -- path given for config file either not a file or not read write

4 -- pyproject.toml config file parse issue. Use validate-pyproject on it then try again

5 -- Backend not supported. Need to add support for that backend. Submit an issue

6 -- The pyproject.toml depends on the requirements folders and files. Create them

7 -- For locking dependencies, pip-tools package must be installed. Not installed

8 -- The snippet is invalid. Either nested snippets or start stop token out of order. Fix the snippet then try again

9 -- In pyproject.toml, there is no snippet with that snippet code

Command options
-----------------

.. csv-table:: :code:`reqs fix` options
   :header: cli, default, description
   :widths: auto

   "-p/--path", "cwd", "absolute path to package base folder"
   "-v/--venv-relpath", "None", "venv relative path. None implies all venv use the same python interpreter version"
   "-t/--timeout", "15", "Web connection time in seconds"
   "--show-unresolvables", "True", "For each venv, in a table print the unresolvable dependency conflicts"
   "--show-fixed", "True", "For each venv, in a table print fixed issues"
   "--show-resolvable-shared", "True", "For each venv in a table print resolvable issues that involve .shared.in files"
