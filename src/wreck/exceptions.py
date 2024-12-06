"""
.. moduleauthor:: Dave Faulkmore <https://mastodon.social/@msftcangoblowme>

Package wide exceptions

.. py:data:: __all__
   :type: tuple[str, str]
   :value: ("PyProjectTOMLParseError", "MissingRequirementsFoldersFiles")

   Module exports

"""

__package__ = "wreck"
__all__ = (
    "MissingPackageBaseFolder",
    "MissingRequirementsFoldersFiles",
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
