__all__ = (
    "ArbitraryEqualityNotImplemented",
    "MissingPackageBaseFolder",
    "MissingRequirementsFoldersFiles",
    "PinMoreThanTwoSpecifiers",
)

class ArbitraryEqualityNotImplemented(NotImplementedError):
    def __init__(self, msg: str) -> None: ...

class MissingRequirementsFoldersFiles(AssertionError):
    def __init__(self, msg: str) -> None: ...

class MissingPackageBaseFolder(AssertionError):
    def __init__(self, msg: str) -> None: ...

class PinMoreThanTwoSpecifiers(NotImplementedError):
    def __init__(self, msg: str) -> None: ...
