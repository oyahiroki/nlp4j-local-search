"""Result objects returned by DataPipeline terminal operations."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class LoadResult:
    """Immutable result of a DataPipeline.load() execution."""

    read_count: int
    """Number of documents read from the source."""

    loaded_count: int
    """Number of documents successfully added to the index."""

    written_count: int
    """Number of documents written to the output file (0 if save_as was not called)."""

    elapsed_seconds: float
    """Elapsed time in seconds."""

    output_path: Optional[Path]
    """Output file path if save_as() was called, otherwise None."""

    def __str__(self) -> str:
        return (
            f"Loaded {self.loaded_count:,} documents "
            f"in {self.elapsed_seconds:.2f} seconds."
        )

    __repr__ = __str__


@dataclass(frozen=True)
class WriteResult:
    """Immutable result of a DataPipeline.write_jsonl() execution."""

    path: str
    """Output file path."""

    count: int
    """Number of documents written."""

    elapsed_seconds: float
    """Elapsed time in seconds."""

    def __str__(self) -> str:
        return (
            f"Wrote {self.count:,} documents "
            f"to {self.path} "
            f"in {self.elapsed_seconds:.2f} seconds."
        )

    __repr__ = __str__
