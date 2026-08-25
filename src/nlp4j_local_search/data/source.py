"""DataSource — streaming source protocol and JsonlSource implementation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator, Protocol, runtime_checkable


@runtime_checkable
class DataSource(Protocol):
    """Protocol for document sources.

    Implementations must yield ``dict`` objects one by one to support
    streaming (constant-memory) processing regardless of file size.
    """

    def __iter__(self) -> Iterator[dict]:
        ...


class JsonlSource:
    """Streaming JSONL source.

    Reads one JSON document per line without loading the entire file
    into memory. Empty lines are silently skipped.

    Example::

        for doc in JsonlSource("data.jsonl"):
            print(doc)
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def __iter__(self) -> Iterator[dict]:
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)

    def to_config(self) -> dict:
        """Return a JSON-serialisable representation of this source."""
        return {
            "type": "jsonl",
            "path": str(self.path),
        }
