"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Package wide exceptions

.. py:data:: __all__
   :type: tuple[str, str, str, str]
   :value: ("ArbitraryEqualityNotImplemented", "MissingPackageBaseFolder", \
   "MissingRequirementsFoldersFiles", "PinMoreThanTwoSpecifiers")

   Module exports

"""

__package__ = "wreck"
__all__ = (
    "ArbitraryEqualityNotImplemented",
    "MissingPackageBaseFolder",
    "MissingRequirementsFoldersFiles",
    "PinMoreThanTwoSpecifiers",
)


class MissingRequirementsFoldersFiles(AssertionError):
    """Neglected to create/prepare requirements folders and ``.in`` files.

    Unabated would produce an empty string snippet. Instead provide
    user feedback

    :ivar msg: The error message
    :vartype msg: str
    """

    def __init__(self, msg: str) -> None:
        """Class constructor."""
        super().__init__(msg)


class MissingPackageBaseFolder(AssertionError):
    """Loader did not provide package base folder. Do not know the cwd

    :ivar msg: The error message
    :vartype msg: str
    """

    def __init__(self, msg: str) -> None:
        """Class constructor."""
        super().__init__(msg)


class ArbitraryEqualityNotImplemented(NotImplementedError):
    """``===`` operator is not yet supported.

    Convert this exception into an UnResolvable. End user
    would have to manually handle the issue.

    :ivar msg: The error message
    :vartype msg: str
    """

    def __init__(self, msg: str) -> None:
        """Class constructor."""
        super().__init__(msg)


class PinMoreThanTwoSpecifiers(NotImplementedError):
    """A pin has ``>2`` specifiers. e.g. >=2.5.6, !=2.5.7, <2.7

    Convert this exception into an UnResolvable. End user
    would have to manually handle the issue.

    :ivar msg: The error message
    :vartype msg: str
    """

    def __init__(self, msg: str) -> None:
        """Class constructor."""
        super().__init__(msg)
