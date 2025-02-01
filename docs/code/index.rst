Code manual
============

.. Apache 2.0 https://github.com/google/material-design-icons
.. Browse Google Material Symbol icons https://fonts.google.com/icons
.. colors https://sphinx-design.readthedocs.io/en/latest/css_classes.html#colors

.. grid:: 2
   :margin: 3
   :padding: 2
   :gutter: 3 3 3 3

   .. grid-item-card:: :material-twotone:`login;2em;sd-text-success` Entrypoints
      :class-card: sd-border-0

      - :doc:`cli_dependencies`

   .. grid-item-card:: :material-twotone:`lock_open;2em;sd-text-success` fix requirements
      :class-card: sd-border-0

      - :doc:`collections <core/lock_collections>`
      - :doc:`filepins <core/lock_filepins>`
      - :doc:`discrepancy <core/lock_discrepancy>`
      - :doc:`loader <core/lock_loader>`
      - :doc:`datum <core/lock_datum>`
      - :doc:`util <core/lock_util>`

   .. grid-item-card:: :material-twotone:`foundation;2em;sd-text-muted` Core
      :class-card: sd-border-0

      - :doc:`Constants <general/constants>`
      - :doc:`Version file <general/version_file>`
      - :doc:`Exceptions <general/exceptions>`
      - :doc:`Check type <general/check_type>`
      - :doc:`pyproject.toml read <general/pep518_read>`
      - :doc:`pyproject.toml venvs <general/pep518_venvs>`
      - :doc:`Package installed <general/package_installed>`
      - :doc:`Run command <general/run_cmd>`
      - :doc:`pyproject.toml read patch <monkey/patch_pyproject_reading>`
      - :doc:`pyproject.toml read base <monkey/pyproject_reading>`

.. module:: wreck
   :platform: Unix
   :synopsis: package level exports

    .. py:data:: wreck.__all__
       :type: tuple[str, str]
       :value: ("MissingPackageBaseFolder", "MissingRequirementsFoldersFiles")

       Package level exports are limited to just custom exceptions. This was originally
       done to avoid unexpected side effects
