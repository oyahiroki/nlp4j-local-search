# SearchResult のPython側ラッパー
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class SearchResult:
    id: str
    body: Optional[str]
    score: float
    data: Optional[str] = None

    @classmethod
    def from_java(cls, obj: Any) -> "SearchResult":
        java_body = getattr(obj, "body", None)
        java_data = getattr(obj, "data", None)

        return cls(
            id=str(obj.id),
            body=None if java_body is None else str(java_body),
            score=float(obj.score),
            data=None if java_data is None else str(java_data),
        )
