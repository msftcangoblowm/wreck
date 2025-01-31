Dependencies
==============

Requirements files
-------------------

Required and Optional dependencies are broken into lots and lots of requirements which
are interlinked, e.g:

.. code:: text

   requirements/pins.shared.in
   requirements/pip.in
   requirements/pip-tools.in
   requirements/dev.in
   requirements/kit.in
   requirements/mypy.in
   requirements/manage.in
   requirments/prod.shared.in
   requirments/tox.in
   docs/requirements.in

An author only apply constraints in the most dire circumstances. This
happens only within ``pins.shared.in``. Equivalent to a .lock file, so ``-c``
is not allowed.

Although should be obvious, it's not stated often enough; ``*.in`` files
should only contains top level (direct package) dependencies.

.. code:: text

   requirements/pins.shared.in   # included by others
   requirements/pip.in           # requirements/pip.lock
   requirements/pip-tools.in     # requirements/pip-tools.lock
   requirements/dev.in           # requirements/dev.lock
   requirements/kit.in           # requirements/kit.lock
   requirements/mypy.in          # requirements/mypy.lock
   requirements/manage.in        # requirements/manage.lock
   requirments/prod.shared.in    # requirments/prod.shared.lock Included by others
   requirments/tox.in            # requirments/tox.lock
   docs/requirements.in          # docs/requirements.lock


pyproject.toml file
---------------------

Then link this to your ``pyproject.toml`` file

.. code:: text

   [build-system]
   requires = [
       "setuptools>=70.0.0",
       "wheel",
       "build",
       "click",
   ]
   build-backend = "setuptools.build_meta"

   [project]
   # When --package-name is not provided, gets it from here
   name = "wreck"

   # static is not supported
   dynamic = [
       "optional-dependencies",
       "dependencies",
       "version",
   ]
   # Used by swamp-drain. Grabs name from first entry. Then grabs the first name
   authors = [
       {name = "Dave Faulkmore", email = "faulkmore@protonmail.com"},
   ]

   [tool.setuptools.dynamic]
   dependencies = { file = ['requirements/prod.shared.unlock'] }
   optional-dependencies.pip = { file = ['requirements/pip.lock'] }
   optional-dependencies.pip_tools = { file = ['requirements/pip-tools.lock'] }
   optional-dependencies.dev = { file = ['requirements/dev.lock'] }
   optional-dependencies.manage = { file = ['requirements/manage.lock'] }
   optional-dependencies.docs = { file = ['docs/requirements.lock'] }

   # replace [your package] is app name (underscores, not hyphens)
   version = {attr = "[your package]._version.__version__"}

   # Each venv relative path is predetermined
   # Into which venv goes which requirements is predetermined
   # TOML format, paths **must be** single quoted
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
       'requirements/prod.shared',
   ]

Each and every package author might not have a clue a dependency has a
vulnerability and if the end user chooses to use a ``downgrade`` version
they should be able to do so.

Package authors create ``.in`` file. The ``.lock`` and ``.unlock`` are
produced by :command:`reqs fix`

To unlock dependencies

:command:`reqs unlock`

pins.shared.in
---------------

An example pins.shared.in

This file does not produce a .lock or .unlock files. Consider it a
``.lock`` file. So all :command:`pip-compile` options must already be resolved

.. code:: text

   # strictyaml --> python-dateutil --> prod.shared.lock
   # python -m piptools compile does not see this postrelease. Instead chooses python-dateutil-2.8.2
   python-dateutil==2.9.0.post0

Rode to dependency hell
""""""""""""""""""""""""

In rare cases, may have to manually edit .lock files. Only after discovering which
causes the dependency conflict.

Created two python packages, each with strictyaml as a dependency.
:code:`piptools compile` chose ``python-dateutil-2.8.2`` for one and
``python-dateutil-2.9.0.post0`` for the other

Needed to figure this out. And it's not fun. This is referred to as *dependency hell*!

The ``pins.shared.in`` file is only for really really bad situations where
a package author had no choice but to step in.

This issue, actually, is better handled by the end user using :command:`uv`
with ``--override`` option, rather than hardcoding a constraint.

constraints
------------

``-c [relative path to requirements .in file]`` is a constraint file.
In constraints files, there is no support for:

- ``-r`` requirements files

- .lock files

``dev.in``

.. code:: text

   -c pins.shared.in
   -c prod.shared.in

   black
   blackdoc
   isort
   flake8
   flake8-pyproject
   mypy
   coverage
   twine
   validate-pyproject

``prod.in``

.. code:: text

   -c pins.shared.in

   typing-extensions  # backporting latest greatest typing features
   strictyaml         # yaml spec subset validate and parse
   appdirs            # Adhere to XDG spec
   attrs

``dev.in``

.. code:: text

   # strictyaml --> python-dateutil --> prod.shared.lock
   # python -m piptools compile does not see this postrelease. Instead chooses python-dateutil-2.8.2
   python-dateutil==2.9.0.post0

   typing-extensions  # backporting latest greatest typing features
   strictyaml         # yaml spec subset validate and parse
   appdirs            # Adhere to XDG spec
   attrs

   black
   blackdoc
   isort
   flake8
   flake8-pyproject
   mypy
   coverage
   twine
   validate-pyproject

Meaning it's KISS and not compiled. ``pip-tools`` understands this.
These don't understand: build, setuptools, and pip
