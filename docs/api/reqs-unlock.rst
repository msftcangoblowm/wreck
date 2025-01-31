reqs unlock
============

This command is depreciated. Do not use this command.

In the past, would create the ``.unlock`` file without applying any
fixes it.

The v2 algo process leverages knowledge gleened while fixing the
``.lock`` files. Applying that knowledge to know how to fix the ``.unlock``
files.

So if the .lock file was never fixed, ``.unlock`` files couldn't be either.

Whats the point of creating broken ``.unlock`` files?

Don't bother!

Normal usage
-------------

.. code-block:: shell

   reqs unlock --venv-relpath='.venv'

Example results
-----------------

Legacy command. Create ``.unlock`` files in their respective folders
When not all venv use the same Python interpreter version, recommend to use tox or nox.

Excerpt from ``pyproject.toml``

.. code-block:: text

   [tool.setuptools.dynamic]
   dependencies = { file = ["requirements/prod.unlock"] }
   optional-dependencies.dev = { file = ["requirements/dev.lock"] }
   optional-dependencies.kit = { file = ["requirements/kit.lock"] }
   optional-dependencies.pip = { file = ["requirements/pip.lock"] }
   optional-dependencies.pip_tools = { file = ["requirements/pip-tools.lock"] }
   optional-dependencies.manage = { file = ["requirements/manage.lock"] }
   optional-dependencies.mypy = { file = ["requirements/mypy.lock"] }
   optional-dependencies.tox = { file = ["requirements/tox.lock"] }
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
       'requirements/prod',
   ]

Exit codes
-----------

0 -- Evidently sufficient effort put into unittesting. Job well done, beer on me!

2 -- entrypoint incorrect usage

3 -- path given for config file reverse search cannot find a pyproject.toml file

4 -- pyproject.toml config file parse issue. Expecting [[tool.wreck.venvs]] sections

6 -- Missing some .in files. Support file(s) not checked

7 -- venv base folder does not exist. Create it

8 -- expecting [[tool.wreck.venvs]] field reqs to be a sequence

9 -- No such venv found

Command options
-----------------

.. csv-table:: :code:`reqs unlock` options
   :header: cli, default, description
   :widths: auto

   "-p/--path", "cwd", "absolute path to package base folder or pyproject.toml file"
   "-v/--venv-relpath", "None", "Relative to package base folder, path to the venv folder"
