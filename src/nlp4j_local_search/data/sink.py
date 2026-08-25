"""JsonlSink — writes processed documents to a JSONL file."""
from __future__ import annotations

import json
from pathlib import Path
from types import TracebackType
from typing import Optional, Type


class JsonlSink:
    """Context-manager that writes one JSON document per line.

    Example::

        with JsonlSink("output.jsonl") as sink:
            sink.write({"id": 1, "text": "hello"})
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._file = None

    def __enter__(self) -> "JsonlSink":
        self._file = open(self.path, "w", encoding="utf-8")
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None

    def write(self, doc: dict) -> None:
        """Write a single document as a JSON line."""
        if self._file is None:
            raise RuntimeError("JsonlSink must be used as a context manager.")
        self._file.write(json.dumps(doc, ensure_ascii=False) + "\n")
