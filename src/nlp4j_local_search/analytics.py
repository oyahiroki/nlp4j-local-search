from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class AnalyticsKeyword:
    """Represents the keyword identity of a bucket (Java AnalyticsKeyword).

    Attributes:
        field: The aggregation field name.
        lex:   The lexical form (bucket key).
    """

    field: str
    lex: str


@dataclass(frozen=True)
class AnalyticsQuery:
    """Represents the query that produced an AnalyticsResult (Java AnalyticsQuery).

    Attributes:
        kind:         ``"FIELD_VALUE"`` or ``"LUCENE"``.
        field:        Query field (set for ``FIELD_VALUE`` queries).
        value:        Query value (set for ``FIELD_VALUE`` queries).
        lucene_query: Lucene query string (set for ``LUCENE`` queries).
    """

    kind: str
    field: Optional[str] = None
    value: Optional[str] = None
    lucene_query: Optional[str] = None

    @classmethod
    def from_java(cls, value: object) -> "AnalyticsQuery":
        def _str_or_none(v: object) -> Optional[str]:
            if v is None:
                return None
            s = str(v)
            return None if s in ("None", "null", "") else s

        kind_obj = value.getKind()
        kind_str = str(kind_obj) if kind_obj is not None else "FIELD_VALUE"

        return cls(
            kind=kind_str,
            field=_str_or_none(value.getField()),
            value=_str_or_none(value.getValue()),
            lucene_query=_str_or_none(value.getLuceneQuery()),
        )


@dataclass(frozen=True)
class AnalyticsBucket:
    """A single bucket in an AnalyticsResult."""

    field: str
    key: str
    count: int
    all_count: int
    relative_rate: float
    keyword: Optional[AnalyticsKeyword] = None

    @classmethod
    def from_java(cls, value: object) -> "AnalyticsBucket":
        keyword: Optional[AnalyticsKeyword] = None
        try:
            kw = value.getKeyword()
            if kw is not None:
                keyword = AnalyticsKeyword(
                    field=str(kw.getField()),
                    lex=str(kw.getLex()),
                )
        except Exception:
            pass

        return cls(
            field=str(value.getField()),
            key=str(value.getKey()),
            count=int(value.getCount()),
            all_count=int(value.getAllCount()),
            relative_rate=float(value.getRelativeRate()),
            keyword=keyword,
        )


@dataclass(frozen=True)
class AnalyticsResult:
    """Result of a relativeRate analytics query.

    For field-value queries:   query_field and query_value are set.
    For Lucene queries:        lucene_query is set; query_field/query_value are None.

    The ``query`` attribute (AnalyticsQuery) mirrors Java's AnalyticsQuery model
    and is populated when available.  The flat ``query_field`` / ``query_value`` /
    ``lucene_query`` attributes are kept for backward compatibility.
    """

    field: str
    count: int
    total_count: int
    buckets: List[AnalyticsBucket]

    query: Optional[AnalyticsQuery] = None

    # backward compatibility
    query_field: Optional[str] = None
    query_value: Optional[str] = None
    lucene_query: Optional[str] = None

    def __post_init__(self) -> None:
        if self.count < 0:
            raise ValueError(f"count must be >= 0, got {self.count}")
        if self.total_count < 0:
            raise ValueError(f"total_count must be >= 0, got {self.total_count}")
        if self.count > self.total_count:
            raise ValueError(
                f"count ({self.count}) must be <= total_count ({self.total_count})"
            )

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

        # Populate AnalyticsQuery if Java exposes getQuery()
        analytics_query: Optional[AnalyticsQuery] = None
        try:
            jq = value.getQuery()
            if jq is not None:
                analytics_query = AnalyticsQuery.from_java(jq)
        except Exception:
            pass

        return cls(
            field=str(value.getField()),
            count=int(value.getCount()),
            total_count=int(value.getTotalCount()),
            buckets=buckets,
            query=analytics_query,
            query_field=_str_or_none(value.getQueryField()),
            query_value=_str_or_none(value.getQueryValue()),
            lucene_query=_str_or_none(value.getLuceneQuery()),
        )
