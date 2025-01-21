Duplicate lines
================

Describe the problem
---------------------

:code:`reqs fix --venv-relpath='.venv'` was creating a ``dev.unlock``
file with duplicate ``logging-strict>=1.5.0`` lines.

Utterly and miserably failed at reproducing the situation or tracking down the cause.

This hypothesise turned out to be incorrect::

   Both ``dev.in`` and ``prod.in`` have the same requirement line, ``logging-strict>=1.5.0``
   ``dev.in`` includes ``prod.in`` using ``-r``

   Compiling .unlock **expected** ``dev.unlock`` to contain two ``logging-strict>=1.5.0``
   lines

This did not reproduce the cause.

Ensuring the fix works, duplicate lines are removed, is good enough.

The cause remains an unsolved mystery.
