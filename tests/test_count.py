"""Tests for SearchEngine.count()

Covers:
  - count() returns total document count
  - count(query) returns filtered count
  - count(query, filters=) returns further filtered count
  - count(filters=) with no query
  - count() returns int
  - count() on empty index returns 0
  - InvalidDocumentError from invalid filters propagates (not wrapped)
  - closed engine raises JavaSearchError
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from nlp4j_local_search import SearchEngine
from nlp4j_local_search.errors import JavaSearchError

# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

DOCS = [
    {"id": "1", "body": "Kyoto is a historic city in Japan.",
     "category": "city",    "country": "Japan"},
    {"id": "2", "body": "Tokyo is the capital city of Japan.",
     "category": "city",    "country": "Japan"},
    {"id": "3", "body": "Paris is the capital city of France.",
     "category": "city",    "country": "France"},
    {"id": "4", "body": "Nintendo is headquartered in Kyoto, Japan.",
     "category": "company", "country": "Japan"},
    {"id": "5", "body": "Sony is a Japanese multinational company.",
     "category": "company", "country": "Japan"},
    {"id": "6", "body": "Microsoft is headquartered in Redmond, USA.",
     "category": "company", "country": "USA"},
]


@pytest.fixture(scope="module")
def engine():
    with SearchEngine("en", auto_analyze=False) as eng:
        for doc in DOCS:
            eng.add_json(doc)
        eng.commit()
        yield eng


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

def test_count_returns_int(engine):
    result = engine.count()
    assert isinstance(result, int)


# ---------------------------------------------------------------------------
# count() — no arguments (total)
# ---------------------------------------------------------------------------

def test_count_all(engine):
    assert engine.count() == 6


# ---------------------------------------------------------------------------
# count(query) — Lucene query
# ---------------------------------------------------------------------------

def test_count_bare_term(engine):
    assert engine.count("Kyoto") == 2  # id=1, id=4


def test_count_field_qualified(engine):
    assert engine.count("category:city") == 3


def test_count_and_query(engine):
    assert engine.count("category:company AND country:Japan") == 2  # id=4, id=5


def test_count_no_match(engine):
    assert engine.count("ZZZNOMATCHZZ") == 0


# ---------------------------------------------------------------------------
# count(query, filters=) — combined
# ---------------------------------------------------------------------------

def test_count_query_with_filters(engine):
    # "Kyoto" + category=company → id=4 only
    result = engine.count("Kyoto", filters={"category": "company"})
    assert result == 1


def test_count_query_with_filters_no_match(engine):
    result = engine.count("Kyoto", filters={"category": "nonexistent"})
    assert result == 0


# ---------------------------------------------------------------------------
# count(filters=) — filters only, no query
# ---------------------------------------------------------------------------

def test_count_filters_only(engine):
    """count(filters=...) with no query counts by filter only."""
    result = engine.count(filters={"category": "city"})
    assert result == 3  # id=1, 2, 3


def test_count_filters_only_no_match(engine):
    result = engine.count(filters={"category": "nonexistent"})
    assert result == 0


def test_count_filters_only_multiple(engine):
    """Multiple filters are AND-combined."""
    result = engine.count(filters={"category": "company", "country": "Japan"})
    assert result == 2  # id=4, id=5


# ---------------------------------------------------------------------------
# count() on empty index
# ---------------------------------------------------------------------------

def test_count_empty_index():
    with SearchEngine("en", auto_analyze=False) as eng:
        eng.commit()
        assert eng.count() == 0


# ---------------------------------------------------------------------------
# InvalidDocumentError propagation (not wrapped in JavaSearchError)
# ---------------------------------------------------------------------------

def test_invalid_filter_key_raises_invalid_document_error(engine):
    """count() must propagate InvalidDocumentError from _to_java_string_map."""
    from nlp4j_local_search.errors import InvalidDocumentError
    with pytest.raises(InvalidDocumentError):
        engine.count(filters={"": "value"})  # empty key is invalid


def test_invalid_filter_value_raises_invalid_document_error(engine):
    """count() must propagate InvalidDocumentError for non-string filter value."""
    from nlp4j_local_search.errors import InvalidDocumentError
    with pytest.raises(InvalidDocumentError):
        engine.count(filters={"category": 123})  # type: ignore[dict-item]


# ---------------------------------------------------------------------------
# Closed engine
# ---------------------------------------------------------------------------

def test_closed_engine_raises():
    with SearchEngine("en", auto_analyze=False) as eng:
        eng.add("1", "test")
        eng.commit()

    with pytest.raises(JavaSearchError):
        eng.count()
