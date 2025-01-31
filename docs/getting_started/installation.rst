Installation
=============

``wreck`` is available at PyPi :pypi_org:`wreck`,
and can be installed from ``pip`` or source as follows.

.. card::

    .. tabs::

        .. code-tab:: bash From binary wheel

            python -m pip install wreck

        .. code-tab:: bash From source

            git clone https://github.com/msftcangoblowm/wreck
            cd wreck
            python -m venv .venv
            . .venv/bin/activate
            python -m pip install -r requirements/kit.lock -r requirements/prod.lock
            python -m build
            python -m pip install --force-reinstall --no-deps dist/wreck-0.1.0-py3-none-any.whl

.. raw:: html

    <div class="white-space-5px"></div>

- Release tarball and wheel that are uploaded to pypi, is created by Github CI/CD . Not the author.

- How to setup pyenv is explained in :doc:`../contributing`

Configuration
--------------

In pyproject.toml, for each venv, add a ``[[tool.venv]]`` section.

Sample venv for production and dev tools.

.. code-block:: text

   [[tool.wreck.venvs]]
   venv_base_path = '.venv'
   reqs = [
       'requirements/pip',
       'requirements/pip-tools',
       'requirements/prod',
       'requirements/dev',
       'requirements/manage',
       'requirements/kit',
       'requirements/mypy',
       'requirements/tox',
   ]

Sample venv for docs

.. code-block:: text

   [[tool.wreck.venvs]]
   venv_base_path = '.doc/.venv'
   reqs = [
       'docs/requirements',
       'docs/pip-tools',
   ]

These are top most level requirement files without **last** suffix.

The additional requirements are for use by tox and CI/CD workflows.

- use posix relative paths. Yes! Windows users too

- assumes venvs are within the package base folder

- requirements and constraints files are not required to be in a subfolder,
  however it's highly encouraged

package author
"""""""""""""""

Possible corresponding dependency section

.. code-block:: text

   [tool.setuptools.dynamic]

   dependencies = { file = ['requirements/prod.unlock'] }
   optional-dependencies.pip = { file = ['requirements/pip.lock'] }
   optional-dependencies.pip_tools = { file = ['requirements/pip-tools.lock'] }
   optional-dependencies.dev = { file = ['requirements/dev.lock'] }
   optional-dependencies.manage = { file = ['requirements/manage.lock'] }
   optional-dependencies.docs = { file = ['docs/requirements.lock'] }

Dependencies last suffix is ``.unlock``

apps author
""""""""""""

Possible corresponding dependency section

.. code-block:: text

   [tool.setuptools.dynamic]
   dependencies = { file = ['requirements/prod.lock'] }
   optional-dependencies.pip = { file = ['requirements/pip.lock'] }
   optional-dependencies.pip_tools = { file = ['requirements/pip-tools.lock'] }
   optional-dependencies.dev = { file = ['requirements/dev.lock'] }
   optional-dependencies.manage = { file = ['requirements/manage.lock'] }
   optional-dependencies.docs = { file = ['docs/requirements.lock'] }

Dependencies last suffix is ``.lock``
