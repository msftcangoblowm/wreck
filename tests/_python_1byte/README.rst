pip-compile produces 1B file
=============================

Confusion started by testing the file size after touch.

.. code-block:: shell

   touch foo
   stat -c %s foo

0

.. code-block:: shell

   touch empty.in
   pip-compile -o empty.lock empty.in
   stat -c %s empty.in
   stat -c %s empty.lock

.. code-block:: text

   0
   1

File produced is 1B. This is Python thing. EOL/EOF marker is always created.
