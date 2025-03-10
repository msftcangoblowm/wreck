Version file
=============

About setuptools-scm
---------------------

The best thing is automated management of package assets. There is little
need for ``MANIFEST.in``. Don't even need it **unless** explicitly
removing files or folders from the package.

The auto-generated version file is nice. But automated bumping of the
version is silly. The next version is not necessary the new patch version. Semantic
version str are more rich than that. So any code which manages the version file
is a joke.

The only thing that is important is to confirm that the semantic version str is valid.

Managing version file
----------------------

The version file is manually edited.

Initialized, once, using setuptools-scm. After that setuptools-scm is not needed.

The counter-argument maybe might forget or make a mistake. But this is
a non-issue.

It's Part of the release and commit process. Which is documented in ``howto.txt``.

Any doctor that has any value at all has a checklist and follows it.

Version file location
-------------------------

In pyproject.toml,

.. code-block:: text

   [project]
   dynamic = [
       "optional-dependencies",
       "dependencies",
       "version",
   ]

   [tool.setuptools.dynamic]
   version = {attr = "wreck._version.__version__"}

.. py:data:: __version__
   :type: str

   The semantic version, e.g. "0.0.1". This is the full semantic string which can
   include development, pre and post releases, and release candidates

.. py:data:: __version_tuple__
   :type: tuple[int | str, ...]

   Full semantic string as a tuple

Aliases --> Unused

.. py:data:: version
   :type: str

   Alias of __version__

.. py:data:: version_tuple
   :type: tuple[int | str, ...]

   Alias of __version_tuple__
