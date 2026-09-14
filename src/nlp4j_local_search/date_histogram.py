from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DateHistogramBucket:
    """A single DATE histogram bucket."""

    key: str
    doc_count: int

    @classmethod
    def from_java(cls, value: Any) -> "DateHistogramBucket":
        return cls(
            key=str(value.getKeyAsString()),
            doc_count=int(value.getDocCount()),
        )
