reqs
=====

.. py:module:: wreck.cli_dependencies
   :platform: Unix
   :synopsis: Entrypoint reqs

   Entrypoint for dependency fix and legacy unlock fix_v1

   .. py:data:: entrypoint_name
      :type: str
      :value: "reqs"

      Command line entrypoint file name

   .. py:data:: help_path
      :type: str

      cli option ``--path`` doc string

   .. py:data:: help_venv_path
      :type: str

      cli option ``--venv-relpath`` doc string

   .. py:data:: help_timeout
      :type: str

      cli option ``--timeout`` doc string

   .. py:data:: help_is_dry_run
      :type: str

      cli option ``--dry-run`` doc string

   .. py:data:: help_show_unresolvables
      :type: str

      cli option ``--show-unresolvables`` doc string

   .. py:data:: help_show_fixed
      :type: str

      cli option ``--show-fixed`` doc string

   .. py:data:: help_show_resolvable_shared
      :type: str

      cli option ``--show-resolvable-shared`` doc string

   .. py:data:: EPILOG_FIX_V2
      :type: str

      Exit codes explanation for command, ``fix``

   .. py:data:: EPILOG_UNLOCK
      :type: str

      Exit codes explanation for command, ``unlock``

   .. py:function:: main()

      :command:`reqs --help`, prints help

      :command:`reqs COMMAND --help`, prints help for a command

      .. csv-table:: Commands
         :header: command, creates, desc
         :widths: auto

         :py:func:`fix <wreck.cli_dependencies.requirements_fix_v2>`, ".lock", "Create lock and unlock fix both"
         :py:func:`unlock <wreck.cli_dependencies.requirements_unlock>`, ".unlock", "Create unlock dependency file. Legacy algo"

   .. autofunction:: wreck.cli_dependencies.present_results

   .. autofunction:: wreck.cli_dependencies.requirements_fix_v2

   .. autofunction:: wreck.cli_dependencies.requirements_unlock
