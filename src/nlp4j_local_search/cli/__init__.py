"""nlp4j_local_search.cli — command-line utilities for nlp4j-local-search.

Subpackages:
- data: Interactive data shell (nlp4j-data)
- search: Local search CLI (nlp4j-local-search)
"""
from .data.shell import DataShell, main as data_main
from .data.context import DataShellContext, CommandError
from .data.commands import build_default_registry
from .search.main import main as search_main

# Keep `main` pointing to data_main for backwards compatibility if referenced
main = data_main

__all__ = [
    "DataShell",
    "DataShellContext",
    "CommandError",
    "build_default_registry",
    "main",
    "data_main",
    "search_main",
]
