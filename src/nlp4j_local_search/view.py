from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal, Optional


# ---------------------------------------------------------------------------
# Display helper
# ---------------------------------------------------------------------------

def _truncate(value: Any, width: int = 20) -> str:
    """Display-only truncation — does NOT modify the original value."""
    text = str(value)
    if len(text) <= width:
        return text
    return text[: width - 3] + "..."


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ViewBucket:
    """A single aggregation bucket.

    Attributes:
        key:           The field value (never truncated).
        count:         Document count in the target subset (or all docs when no
                       lucene_query is applied).
        all_count:     Document count in the entire index.  None when no
                       lucene_query is applied (no comparison possible).
        relative_rate: count-rate / all_count-rate.  None when no
                       lucene_query is applied.
    """
    key: Any
    count: int
    all_count: Optional[int] = None
    relative_rate: Optional[float] = None


@dataclass(frozen=True)
class ViewField:
    """Aggregation result for a single field.

    Attributes:
        field:       Field name.
        buckets:     Aggregation buckets (ordered by the sort used at build time).
        count:       Number of matched documents in the subset (relativeRate mode).
                     None in count-only mode.
        total_count: Total documents in the index (relativeRate mode).
                     None in count-only mode.
        interval:    DATE histogram interval (e.g. ``\"year\"``).
                     None for normal aggregation fields.
    """
    field: str
    buckets: list[ViewBucket]
    count: Optional[int] = None
    total_count: Optional[int] = None
    interval: Optional[str] = None


# Type alias for sort key
SortKey = Literal["count", "relative_rate", "key"]


@dataclass(frozen=True)
class ViewResult:
    """Formatted result of engine.view().

    ``str(result)`` / ``repr(result)`` produces a human-readable table
    suitable for Jupyter / REPL inspection.

    The underlying data is always intact:
        result.fields[0].buckets[0].key           # full, un-truncated value
        result.fields[0].buckets[0].relative_rate # None if no lucene_query

    Chain methods return a new ViewResult (immutable):
        result.sort_by("relative_rate").filter(min_relative_rate=1.5)
    """

    fields: list[ViewField]
    lucene_query: Optional[str] = None
    single_field: bool = False
    sort_key: SortKey = "count"

    # ------------------------------------------------------------------
    # Chain methods (return new ViewResult; does not mutate)
    # ------------------------------------------------------------------

    def sort_by(
        self,
        key: SortKey,
        *,
        descending: bool = True,
    ) -> "ViewResult":
        """Return a new ViewResult with buckets sorted by *key*.

        Args:
            key:        ``"count"`` or ``"relative_rate"``.
            descending: Sort order. Default ``True``.

        Example::

            engine.view("part", "maker:Nissan").sort_by("relative_rate")
        """
        def _sort_buckets(buckets: list[ViewBucket]) -> list[ViewBucket]:
            if key == "relative_rate":
                # buckets with None relative_rate go last
                return sorted(
                    buckets,
                    key=lambda b: (b.relative_rate is None, -(b.relative_rate or 0) if descending else (b.relative_rate or 0)),
                    reverse=False,
                )
            else:
                return sorted(
                    buckets,
                    key=lambda b: b.count,
                    reverse=descending,
                )

        new_fields = [
            replace(vf, buckets=_sort_buckets(vf.buckets))
            for vf in self.fields
        ]
        return replace(self, fields=new_fields, sort_key=key)

    def filter(
        self,
        *,
        min_count: Optional[int] = None,
        max_count: Optional[int] = None,
        min_relative_rate: Optional[float] = None,
        max_relative_rate: Optional[float] = None,
    ) -> "ViewResult":
        """Return a new ViewResult with buckets filtered by the given thresholds.

        Args:
            min_count:          Keep buckets with count >= this value.
            max_count:          Keep buckets with count <= this value.
            min_relative_rate:  Keep buckets with relative_rate >= this value.
            max_relative_rate:  Keep buckets with relative_rate <= this value.

        Example::

            engine.view("part", "maker:Nissan") \\
                .filter(min_count=2, min_relative_rate=1.5)
        """
        def _keep(b: ViewBucket) -> bool:
            if min_count is not None and b.count < min_count:
                return False
            if max_count is not None and b.count > max_count:
                return False
            if min_relative_rate is not None:
                if b.relative_rate is None or b.relative_rate < min_relative_rate:
                    return False
            if max_relative_rate is not None:
                if b.relative_rate is None or b.relative_rate > max_relative_rate:
                    return False
            return True

        new_fields = [
            replace(vf, buckets=[b for b in vf.buckets if _keep(b)])
            for vf in self.fields
        ]
        return replace(self, fields=new_fields)

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        if self.single_field:
            return self._format_single_field()
        return self._format_overview()

    def __repr__(self) -> str:
        return str(self)

    # ------------------------------------------------------------------
    # Private formatters
    # ------------------------------------------------------------------

    def _has_relative_rate(self) -> bool:
        for vf in self.fields:
            for b in vf.buckets:
                if b.relative_rate is not None:
                    return True
        return False

    def _format_overview(self) -> str:
        has_rr = self._has_relative_rate()

        lines: list[str] = ["View: aggregatable fields"]

        if self.lucene_query:
            lines.append(f"Lucene query: {self.lucene_query}")

        if has_rr:
            lines.append("Format: field | value (count, relative rate)")
        else:
            lines.append("Format: field | value (document count)")
        lines.append("")

        if not self.fields:
            lines.append("(no aggregatable fields with data)")
            return "\n".join(lines)

        field_width = max(len(item.field) for item in self.fields)

        for item in self.fields:
            if has_rr:
                values = ", ".join(
                    f"{_truncate(b.key)} ({b.count}, {b.relative_rate:.2f}x)"
                    if b.relative_rate is not None
                    else f"{_truncate(b.key)} ({b.count})"
                    for b in item.buckets
                )
            else:
                values = ", ".join(
                    f"{_truncate(b.key)} ({b.count})"
                    for b in item.buckets
                )
            lines.append(f"{item.field:<{field_width}} | {values}")

        return "\n".join(lines)

    def _format_date_histogram(self, item: ViewField) -> str:
        lines = [
            f"View: {item.field}",
            f"Interval: {item.interval}",
        ]

        if self.lucene_query:
            lines.append(f"Lucene query: {self.lucene_query}")

        lines.extend([
            "Values are ordered chronologically.",
            "",
            f"{'Rank':>4}  {'Period':<20} {'Count':>8}",
            f"{'-'*4}  {'-'*20} {'-'*8}",
        ])

        for rank, bucket in enumerate(item.buckets, start=1):
            lines.append(
                f"{rank:>4}  "
                f"{_truncate(bucket.key):<20} "
                f"{bucket.count:>8}"
            )

        return "\n".join(lines)

    def _format_single_field(self) -> str:
        if not self.fields:
            return "View: no data"

        item = self.fields[0]

        if item.interval is not None:
            return self._format_date_histogram(item)

        has_rr = any(b.relative_rate is not None for b in item.buckets)

        lines: list[str] = [f"View: {item.field}"]

        if self.lucene_query:
            lines.append(f"Lucene query: {self.lucene_query}")

        if item.count is not None and item.total_count is not None:
            lines.append(
                f"Matched documents: "
                f"{item.count:,} / {item.total_count:,}"
            )

        if has_rr:
            lines.append("Values are ordered by relative rate.")
        else:
            lines.append("Values are ordered by document count.")
        lines.append("")

        if has_rr:
            lines.append(
                f"{'Rank':>4}  {'Value':<20} {'Count':>8} "
                f"{'All Count':>10} {'Relative Rate':>14}"
            )
            lines.append(
                f"{'-'*4}  {'-'*20} {'-'*8} {'-'*10} {'-'*14}"
            )
            for rank, b in enumerate(item.buckets, start=1):
                rr_str = f"{b.relative_rate:.2f}x" if b.relative_rate is not None else "-"
                ac_str = str(b.all_count) if b.all_count is not None else "-"
                lines.append(
                    f"{rank:>4}  "
                    f"{_truncate(b.key):<20} "
                    f"{b.count:>8} "
                    f"{ac_str:>10} "
                    f"{rr_str:>14}"
                )
        else:
            lines.append(
                f"{'Rank':>4}  {'Value':<20} {'Count':>8}"
            )
            lines.append(f"{'-'*4}  {'-'*20} {'-'*8}")
            for rank, b in enumerate(item.buckets, start=1):
                lines.append(
                    f"{rank:>4}  "
                    f"{_truncate(b.key):<20} "
                    f"{b.count:>8}"
                )

        return "\n".join(lines)
