# SearchResult のPython側ラッパー
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SearchResult:
    id: str
    body: str
    score: float

    @classmethod
    def from_java(cls, obj: Any) -> "SearchResult":
        return cls(
            id=str(obj.id),
            body=str(obj.body),
            score=float(obj.score),
        )