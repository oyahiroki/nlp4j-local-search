from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class AnalyticsBucket:
    """A single bucket in an AnalyticsResult."""

    field: str
    key: str
    count: int
    all_count: int
    relative_rate: float

    @classmethod
    def from_java(cls, value: object) -> "AnalyticsBucket":
        return cls(
            field=str(value.getField()),
            key=str(value.getKey()),
            count=int(value.getCount()),
            all_count=int(value.getAllCount()),
            relative_rate=float(value.getRelativeRate()),
        )


@dataclass(frozen=True)
class AnalyticsResult:
    """Result of a relativeRate analytics query.

    For field-value queries:   query_field and query_value are set.
    For Lucene queries:        lucene_query is set; query_field/query_value are None.
    """

    field: str
    count: int
    total_count: int
    buckets: List[AnalyticsBucket]

    query_field: Optional[str] = None
    query_value: Optional[str] = None
    lucene_query: Optional[str] = None

    @classmethod
    def from_java(cls, value: object) -> "AnalyticsResult":
        buckets = [
            AnalyticsBucket.from_java(bucket)
            for bucket in value.getBuckets()
        ]

        # getLuceneQuery() / getQueryField() / getQueryValue() may return Java null
        def _str_or_none(v: object) -> Optional[str]:
            if v is None:
                return None
            s = str(v)
            return None if s in ("None", "null", "") else s

        return cls(
            field=str(value.getField()),
            count=int(value.getCount()),
            total_count=int(value.getTotalCount()),
            buckets=buckets,
            query_field=_str_or_none(value.getQueryField()),
            query_value=_str_or_none(value.getQueryValue()),
            lucene_query=_str_or_none(value.getLuceneQuery()),
        )
