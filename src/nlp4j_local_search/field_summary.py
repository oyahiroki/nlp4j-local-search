from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


def _truncate_example(
    value: Optional[str],
    width: int = 30,
) -> str:
    """Return a single-line display representation."""
    if value is None:
        return "-"

    # Table output must remain on one line.
    text = str(value).replace("\r", " ").replace("\n", " ")

    if len(text) <= width:
        return text

    return text[: width - 3] + "..."


@dataclass(frozen=True)
class FieldSummary:
    """Summary information for one indexed field."""

    field: str
    kind: str
    aggregatable: bool

    document_count: int

    # None when unavailable.
    documents_with_value: Optional[int] = None
    coverage: Optional[float] = None

    # Available only for aggregatable KEYWORD fields.
    unique_count: Optional[int] = None
    diversity: Optional[float] = None

    # Full value. Truncation is display-only.
    example: Optional[str] = None

    @classmethod
    def from_java(cls, value: Any) -> "FieldSummary":
        has_coverage = bool(value.hasCoverage())
        has_unique = bool(value.hasUniqueValueCount())
        has_diversity = bool(value.hasDiversity())

        example = value.getExample()

        return cls(
            field=str(value.getField()),
            kind=str(value.getKind().name()),
            aggregatable=bool(value.isAggregatable()),
            document_count=int(value.getDocumentCount()),
            documents_with_value=(
                int(value.getDocumentsWithValue())
                if has_coverage
                else None
            ),
            coverage=(
                float(value.getCoverage())
                if has_coverage
                else None
            ),
            unique_count=(
                int(value.getUniqueValueCount())
                if has_unique
                else None
            ),
            diversity=(
                float(value.getDiversity())
                if has_diversity
                else None
            ),
            example=(
                str(example)
                if example is not None
                else None
            ),
        )


@dataclass(frozen=True)
class FieldsSummary:
    """Summary information for all indexed fields."""

    document_count: int
    fields: list[FieldSummary]

    @classmethod
    def from_java(cls, value: Any) -> "FieldsSummary":
        return cls(
            document_count=int(value.getDocumentCount()),
            fields=[
                FieldSummary.from_java(field)
                for field in value.getFields()
            ],
        )

    def __str__(self) -> str:
        lines: list[str] = [
            f"Documents: {self.document_count:,}",
            "",
        ]

        if not self.fields:
            lines.append("(no fields with data)")
            return "\n".join(lines)

        rows: list[list[str]] = []

        for field in self.fields:
            coverage = (
                f"{field.coverage * 100:.2f}%"
                if field.coverage is not None
                else "-"
            )

            unique = (
                f"{field.unique_count:,}"
                if field.unique_count is not None
                else "-"
            )

            diversity = (
                f"{field.diversity * 100:.2f}%"
                if field.diversity is not None
                else "-"
            )

            rows.append([
                field.field,
                field.kind,
                "true" if field.aggregatable else "false",
                coverage,
                unique,
                diversity,
                _truncate_example(field.example),
            ])

        headers = [
            "Field",
            "Type",
            "Aggregatable",
            "Coverage",
            "Unique",
            "Diversity",
            "Example",
        ]

        widths = []

        for index, header in enumerate(headers):
            widths.append(
                max(
                    len(header),
                    max(len(row[index]) for row in rows),
                )
            )

        # Avoid an excessively wide table because of Example.
        widths[6] = min(max(widths[6], len("Example")), 30)

        lines.append(
            f"{headers[0]:<{widths[0]}}  "
            f"{headers[1]:<{widths[1]}}  "
            f"{headers[2]:<{widths[2]}}  "
            f"{headers[3]:>{widths[3]}}  "
            f"{headers[4]:>{widths[4]}}  "
            f"{headers[5]:>{widths[5]}}  "
            f"{headers[6]:<{widths[6]}}"
        )

        lines.append(
            f"{'-' * widths[0]}  "
            f"{'-' * widths[1]}  "
            f"{'-' * widths[2]}  "
            f"{'-' * widths[3]}  "
            f"{'-' * widths[4]}  "
            f"{'-' * widths[5]}  "
            f"{'-' * widths[6]}"
        )

        for row in rows:
            lines.append(
                f"{row[0]:<{widths[0]}}  "
                f"{row[1]:<{widths[1]}}  "
                f"{row[2]:<{widths[2]}}  "
                f"{row[3]:>{widths[3]}}  "
                f"{row[4]:>{widths[4]}}  "
                f"{row[5]:>{widths[5]}}  "
                f"{row[6]:<{widths[6]}}"
            )

        return "\n".join(lines)

    def __repr__(self) -> str:
        return str(self)
