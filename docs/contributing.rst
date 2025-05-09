Contributing
=============

I'm not a coder!
-----------------

Submit an issue explaining the issue thoroughly. Not everyone can code
and there is no shame in that.

End of the day, world+dog wants featureful well written packages which
stay on mission and within the resources and talent at the teams disposal.

.. _contributing-issues-and-prs:

Issues and PRs
---------------

Create an issue first. Get feedback. And if the feedback is favorable,
do the work and submit a PR, in a branch, with a mention to the issue.

The trick is to keep the commit scope as small as possible. Ideally should do only one thing.

PR should come with:

- unittests

- Sphinx in-code documentation. Not dependent upon :ref:`sphinx-ext-napoleon:overview`

If an issue or PR is not dealt with in a
timely manner, optionally can send a reminder to maintainer on mastodon

New features
"""""""""""""

The rules might get tossed aside. Take risk; be bold.

Expect feedback asking for changes. Be patient, make whatever changes are requested.

Setup venvs
------------

Will be setting up two venv

.. csv-table:: Virtual environments
   :header: "code base", "Python version"
   :widths: auto

   "docs", "py310"
   "package", "py39"

Assumes using pyenv

docs venv
""""""""""

pyenv

.. code-block:: shell

   mkdir .doc
   cd .doc
   pyenv versions

Assuming py310 version is ``3.10.14``

.. code-block:: shell

   touch .python-version
   echo "3.10.14" > .python-version

Check active version

.. code-block:: shell

   pyenv version

3.10.14

setup docs venv and install dependencies

.. code-block:: shell

   mkdir -p .doc/.venv
   cd .doc
   python -m venv .venv
   . .venv/bin/activate
   python -m pip install -r ../docs/pip-tools.lock  -r ../docs/requirements.lock
   python -m build

When using :code:`pip install -r` **NEVER** break command into multiple calls.

Update docs requirements
"""""""""""""""""""""""""

activate doc venv then run

.. code-block:: shell

   cd docs
   make doc_upgrade

package venv
"""""""""""""

``.python-version`` goes into the package base folder parent, not the package base folder

.. code-block:: shell

   pyenv version

3.9.16

.. code-block:: shell

   mkdir .venv
   python -m venv .venv
   . .venv/bin/activate
   python -m pip install -r requirements/pip-tools.lock -r requirements/prod.lock -r requirements/kit.lock -r requirements/manage.lock -r requirements/dev.lock

When using :code:`pip install -r` **NEVER** break command into multiple calls.

Everything except docs

Update package requirements
""""""""""""""""""""""""""""

activate package venv then run

.. code-block:: shell

   . .venv/bin/activate
   reqs fix --venv-relpath='.venv'

   cd .tox && tox -r --root=.. -c ../tox-req.ini -e docs --workdir=.; cd - &>/dev/null

The 1st command runs within the current active venv. The packages default. So
the python interpreter version is already known.

The 2nd command lets tox choose the python interpreter version and
create the venv, and run the command. These python interpreter versions are not
the same!

The lock process will upgrade the dependency versions and enforce any
package version restrictions; specifiers and qualifiers are recognized
and applied.

Setup -- tox
--------------

pyenv installed versions

.. code-block:: shell

   pyenv versions

The ``.tox/.python-version`` needs all the versions tox will have access to

.. code-block:: shell

   mkdir .tox
   cd .tox
   touch .python-version
   cat <<-EOF > .python-version
   3.9.16
   3.10.14
   3.11.9
   3.12.4
   pypy3.10-7.3.16
   EOF

Assuming package venv is already activated

.. code-block:: shell

   python -m pip install -r requirements/tox.lock

Then use tox

.. code-block:: shell

   tox -r -e lint
   tox -r -e mypy
   tox -r -e pre-commit
   tox -r -e interrogate
   cd .tox && tox -r --root=.. -c ../tox-test.ini -e pypy3 --workdir=.; cd - &>/dev/null
   tox -r -e docs

``-r`` long form is ``--recreate``. tox only needed to recreate venv when
dependencies change. Or whenever feel the itch.

For running coverage, python version can be changed, e.g. ``-e pypy3``.
