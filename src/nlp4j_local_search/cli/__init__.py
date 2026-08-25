"""nlp4j_local_search.cli — interactive data shell (nlp4j-data)."""
from .shell import DataShell, main
from .context import DataShellContext, CommandError
from .commands import build_default_registry

__all__ = [
    "DataShell",
    "DataShellContext",
    "CommandError",
    "build_default_registry",
    "main",
]
