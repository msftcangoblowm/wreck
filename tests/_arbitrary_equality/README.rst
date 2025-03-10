There is no support for arbitrary equality operator ``===``

Exception ``wreck.exceptions.ArbitraryEqualityNotImplemented`` is raised,
caught, and converted into ``wreck.lock_discrepancy.UnResolvable`` message

The end user is notified that a ``===`` was encountered and can then
manually go in and replace it.

There is the remote possibility, the author had damn good reason for
using this operator. Manually fixing is no fun. Here what that would entails:

- looking at other ``.lock`` and ``.unlock`` files containing the same package.
  Use :command:`grep`

- might contain invalid semantic version e.g. ``1.0+downstream1``,
  arbitrary equality wouldn't match that.

.. seealso::

   `pep#440 arbitrary-equality <https://peps.python.org/pep-0440/#arbitrary-equality>`_
