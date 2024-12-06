These conditions should be separated into independent tests source file folders

nudge pin
----------

prod.in::

    importlib-metadata>=8.5.0

constraints-conflicts.unlock::

    importlib-metadata>=8.5.0

prod.lock::

    importlib-metadata==8.5.1
        # via -r requirements/prod.shared.in

constraints-conflicts.lock::

    # Conflicts with a prod.lock
    importlib-metadata==8.5.2

Ensure importlib-metadata==8.5.2 is always chosen.
Fix .lock, reference .in for pin constraints, then puts nudge pin in .unlock

unresolvable
--------------

constraints-conflicts.unlock::

    pip<24.2

constraints-various.unlock::

    pip>=24.2

becomes
""""""""

``pip-lt.{unlock,lock}`` and ``pip-ge.{unlock,lock}``

auto-fix qualifier
-------------------

constraints-conflicts.unlock::

    colorama;os_name == "nt"
    dolorama;os_name == "nt"

constraints-various.unlock::

    colorama>=0.4.5 ;platform_system=="Windows"
    dolorama>=0.4.6 ;platform_system=="Windows"

Both should become

.. code-block:: text

   colorama>=0.4.5 ;platform_system=="Windows"
   dolorama>=0.4.6 ;platform_system=="Windows"
