__all__ = (
    "MissingPackageBaseFolder",
    "MissingRequirementsFoldersFiles",
)

class MissingRequirementsFoldersFiles(AssertionError):
    def __init__(self, msg: str) -> None: ...

class MissingPackageBaseFolder(AssertionError):
    def __init__(self, msg: str) -> None: ...
