"""Tests for SearchEngine.validate_query()

Covers:
  - validate_query() returns QueryValidationResult
  - valid=True for syntactically correct queries
  - valid=False for malformed queries
  - message is None when valid=True
  - message is non-empty string when valid=False
  - QueryValidationResult is frozen dataclass
  - non-string query raises InvalidDocumentError
  - closed engine raises JavaSearchError
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from nlp4j_local_search import QueryValidationResult, SearchEngine
from nlp4j_local_search.errors import InvalidDocumentError, JavaSearchError


@pytest.fixture(scope="module")
def engine():
    with SearchEngine("ja") as eng:
        eng.add("1", "東京都は日本の都道府県のひとつです")
        eng.commit()
        yield eng


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

def test_validate_query_returns_query_validation_result(engine):
    result = engine.validate_query("京都 AND 寺院")
    assert isinstance(result, QueryValidationResult)


# ---------------------------------------------------------------------------
# Valid queries
# ---------------------------------------------------------------------------

def test_valid_simple_term(engine):
    result = engine.validate_query("京都")
    assert result.valid is True
    assert result.message is None


def test_valid_and_or(engine):
    result = engine.validate_query("京都 AND (寺院 OR 神社)")
    assert result.valid is True


def test_valid_field_query(engine):
    result = engine.validate_query("category:company AND text_en:Kyoto")
    assert result.valid is True


def test_valid_wildcard(engine):
    result = engine.validate_query("text_en:Kyo*")
    assert result.valid is True


def test_valid_phrase(engine):
    result = engine.validate_query('text_en:"historic city"')
    assert result.valid is True


def test_valid_range(engine):
    result = engine.validate_query("year_i:[2025 TO 2026]")
    assert result.valid is True


def test_valid_match_all(engine):
    result = engine.validate_query("*:*")
    assert result.valid is True


# ---------------------------------------------------------------------------
# Invalid queries
# ---------------------------------------------------------------------------

def test_invalid_unclosed_paren(engine):
    result = engine.validate_query("京都 AND (寺院 OR 神社")
    assert result.valid is False
    assert result.message is not None
    assert isinstance(result.message, str)
    assert len(result.message) > 0


def test_invalid_message_is_string(engine):
    result = engine.validate_query("AND OR")
    if not result.valid:
        assert isinstance(result.message, str)


# ---------------------------------------------------------------------------
# QueryValidationResult is a frozen dataclass
# ---------------------------------------------------------------------------

def test_query_validation_result_frozen():
    r = QueryValidationResult(valid=True)
    with pytest.raises((AttributeError, TypeError)):
        r.valid = False  # type: ignore[misc]


def test_query_validation_result_default_message_none():
    r = QueryValidationResult(valid=True)
    assert r.message is None


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_non_string_raises(engine):
    with pytest.raises(InvalidDocumentError):
        engine.validate_query(123)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Closed engine
# ---------------------------------------------------------------------------

def test_closed_engine_raises():
    with SearchEngine("ja") as eng:
        eng.add("1", "test")
        eng.commit()

    with pytest.raises(JavaSearchError):
        eng.validate_query("test")
