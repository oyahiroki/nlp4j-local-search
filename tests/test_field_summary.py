from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from nlp4j_local_search.field_summary import (
    FieldSummary,
    FieldsSummary,
)


# ---------------------------------------------------------------------------
# Fake Java objects (no JVM required)
# ---------------------------------------------------------------------------

class FakeKind:

    def __init__(self, name: str):
        self._name = name

    def name(self):
        return self._name


class FakeJavaFieldSummary:

    def __init__(
        self,
        *,
        field,
        kind,
        aggregatable,
        document_count,
        documents_with_value=-1,
        coverage=-1.0,
        unique_count=-1,
        diversity=-1.0,
        example=None,
        has_coverage=False,
        has_unique=False,
        has_diversity=False,
    ):
        self._field = field
        self._kind = FakeKind(kind)
        self._aggregatable = aggregatable
        self._document_count = document_count
        self._documents_with_value = documents_with_value
        self._coverage = coverage
        self._unique_count = unique_count
        self._diversity = diversity
        self._example = example
        self._has_coverage = has_coverage
        self._has_unique = has_unique
        self._has_diversity = has_diversity

    def getField(self):
        return self._field

    def getKind(self):
        return self._kind

    def isAggregatable(self):
        return self._aggregatable

    def getDocumentCount(self):
        return self._document_count

    def getDocumentsWithValue(self):
        return self._documents_with_value

    def hasCoverage(self):
        return self._has_coverage

    def getCoverage(self):
        return self._coverage

    def hasUniqueValueCount(self):
        return self._has_unique

    def getUniqueValueCount(self):
        return self._unique_count

    def hasDiversity(self):
        return self._has_diversity

    def getDiversity(self):
        return self._diversity

    def getExample(self):
        return self._example


class FakeJavaFieldsSummary:

    def __init__(self, document_count, fields):
        self._document_count = document_count
        self._fields = fields

    def getDocumentCount(self):
        return self._document_count

    def getFields(self):
        return self._fields


# ---------------------------------------------------------------------------
# Tests: FieldSummary.from_java
# ---------------------------------------------------------------------------

def test_keyword_summary_from_java():

    java_field = FakeJavaFieldSummary(
        field="manufacturer_s",
        kind="KEYWORD",
        aggregatable=True,
        document_count=1000,
        documents_with_value=900,
        coverage=0.9,
        unique_count=90,
        diversity=0.1,
        example="NISSAN",
        has_coverage=True,
        has_unique=True,
        has_diversity=True,
    )

    result = FieldSummary.from_java(java_field)

    assert result.field == "manufacturer_s"
    assert result.kind == "KEYWORD"
    assert result.aggregatable is True

    assert result.document_count == 1000
    assert result.documents_with_value == 900

    assert result.coverage == 0.9
    assert result.unique_count == 90
    assert result.diversity == 0.1

    assert result.example == "NISSAN"


def test_numeric_summary_unique_is_none():

    java_field = FakeJavaFieldSummary(
        field="model_year_i",
        kind="INTEGER",
        aggregatable=True,
        document_count=1000,
        documents_with_value=950,
        coverage=0.95,
        unique_count=-1,
        diversity=-1.0,
        example="2024",
        has_coverage=True,
        has_unique=False,
        has_diversity=False,
    )

    result = FieldSummary.from_java(java_field)

    assert result.coverage == 0.95

    assert result.unique_count is None
    assert result.diversity is None

    assert result.example == "2024"


def test_non_aggregatable_values_are_none():

    java_field = FakeJavaFieldSummary(
        field="text",
        kind="TEXT",
        aggregatable=False,
        document_count=1000,
        example="Hello world",
    )

    result = FieldSummary.from_java(java_field)

    assert result.aggregatable is False

    assert result.documents_with_value is None
    assert result.coverage is None
    assert result.unique_count is None
    assert result.diversity is None

    assert result.example == "Hello world"


def test_fields_summary_from_java():

    java_summary = FakeJavaFieldsSummary(
        100,
        [
            FakeJavaFieldSummary(
                field="id",
                kind="KEYWORD",
                aggregatable=False,
                document_count=100,
                example="1",
            ),
            FakeJavaFieldSummary(
                field="maker_s",
                kind="KEYWORD",
                aggregatable=True,
                document_count=100,
                documents_with_value=80,
                coverage=0.8,
                unique_count=4,
                diversity=0.05,
                example="NISSAN",
                has_coverage=True,
                has_unique=True,
                has_diversity=True,
            ),
        ],
    )

    result = FieldsSummary.from_java(java_summary)

    assert result.document_count == 100
    assert len(result.fields) == 2

    assert result.fields[0].field == "id"
    assert result.fields[1].field == "maker_s"


# ---------------------------------------------------------------------------
# Tests: FieldsSummary.__str__
# ---------------------------------------------------------------------------

def test_format_fields_summary():

    summary = FieldsSummary(
        document_count=1000,
        fields=[
            FieldSummary(
                field="id",
                kind="KEYWORD",
                aggregatable=False,
                document_count=1000,
                example="ABC001",
            ),
            FieldSummary(
                field="manufacturer_s",
                kind="KEYWORD",
                aggregatable=True,
                document_count=1000,
                documents_with_value=1000,
                coverage=1.0,
                unique_count=82,
                diversity=0.082,
                example="NISSAN NORTH AMERICA, INC.",
            ),
            FieldSummary(
                field="model_year_i",
                kind="INTEGER",
                aggregatable=True,
                document_count=1000,
                documents_with_value=999,
                coverage=0.999,
                example="2024",
            ),
        ],
    )

    text = str(summary)

    assert "Documents: 1,000" in text

    assert "Field" in text
    assert "Type" in text
    assert "Aggregatable" in text
    assert "Coverage" in text
    assert "Unique" in text
    assert "Diversity" in text
    assert "Example" in text

    assert "manufacturer_s" in text
    assert "100.00%" in text
    assert "82" in text
    assert "8.20%" in text

    assert "model_year_i" in text
    assert "99.90%" in text


def test_format_empty_fields_summary():
    summary = FieldsSummary(document_count=0, fields=[])
    text = str(summary)
    assert "Documents: 0" in text
    assert "(no fields with data)" in text


def test_example_truncated_in_display():
    """Long examples are truncated to 30 chars in display, but stored in full."""
    long_example = "A" * 50
    field = FieldSummary(
        field="data",
        kind="STORED_ONLY",
        aggregatable=False,
        document_count=1,
        example=long_example,
    )
    summary = FieldsSummary(document_count=1, fields=[field])
    text = str(summary)
    # The display line should contain a truncated version ending in "..."
    assert "..." in text
    # But the raw field value is stored in full
    assert field.example == long_example


def test_newline_in_example_replaced():
    """Newlines in example values are replaced with spaces for single-line display."""
    field = FieldSummary(
        field="body",
        kind="TEXT",
        aggregatable=False,
        document_count=1,
        example="line1\nline2",
    )
    summary = FieldsSummary(document_count=1, fields=[field])
    text = str(summary)
    # The newline must not appear in the table output
    lines = text.splitlines()
    # Each data row should be a single line without embedded newlines
    for line in lines:
        assert "\n" not in line
