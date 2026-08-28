# SearchResult / QueryValidationResult のPython側ラッパー
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


@dataclass(frozen=True)
class QueryValidationResult:
    """Lucene クエリの構文検証結果。

    Attributes:
        valid:   構文が正しければ True。
        message: 構文エラーのメッセージ（valid=True の場合は None）。
    """
    valid: bool
    message: Optional[str] = None
