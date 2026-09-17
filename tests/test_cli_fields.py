"""
Tests for SearchCli.fields() after the fields_summary() migration.

No JVM required — uses a FakeEngine stub.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from nlp4j_local_search.cli.search.main import SearchCli
from nlp4j_local_search.field_summary import FieldSummary, FieldsSummary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_summary() -> FieldsSummary:
    return FieldsSummary(
        document_count=100,
        fields=[
            FieldSummary(
                field="maker_s",
                kind="KEYWORD",
                aggregatable=True,
                document_count=100,
                documents_with_value=100,
                coverage=1.0,
                unique_count=5,
                diversity=0.05,
                example="NISSAN",
            ),
        ],
    )


class FakeEngine:

    def fields_summary(self) -> FieldsSummary:
        return _make_summary()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_cli_fields(capsys):
    cli = SearchCli(
        lang="en",
        auto_analyze=False,
    )

    cli.engine = FakeEngine()  # type: ignore[assignment]

    cli.fields()

    output = capsys.readouterr().out

    assert "Documents: 100" in output
    assert "maker_s" in output
    assert "KEYWORD" in output
    assert "true" in output
    assert "100.00%" in output
    assert "5" in output
    assert "5.00%" in output
    assert "NISSAN" in output


def test_cli_fields_execute(capsys):
    """Verify that the 'fields' command string routes to SearchCli.fields()."""
    cli = SearchCli(
        lang="en",
        auto_analyze=False,
    )

    cli.engine = FakeEngine()  # type: ignore[assignment]

    result = cli.execute("fields")

    assert result is True

    output = capsys.readouterr().out
    assert "Documents: 100" in output


def test_cli_fields_execute_with_parens(capsys):
    """'fields()' (with parentheses) should also work."""
    cli = SearchCli(
        lang="en",
        auto_analyze=False,
    )

    cli.engine = FakeEngine()  # type: ignore[assignment]

    result = cli.execute("fields()")

    assert result is True

    output = capsys.readouterr().out
    assert "maker_s" in output
