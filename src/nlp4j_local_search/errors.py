# Python用例外
class SearchEngineError(Exception):
    """Base exception for nlp4j-local-search."""


class JVMStartError(SearchEngineError):
    """Raised when JVM could not be started."""


class JavaSearchError(SearchEngineError):
    """Raised when Java LocalSearch failed."""


class InvalidDocumentError(SearchEngineError):
    """Raised when document input is invalid."""