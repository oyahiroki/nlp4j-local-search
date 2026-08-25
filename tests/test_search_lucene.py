"""Tests for SearchEngine.search_lucene()

Covers:
  - Basic keyword query (no field prefix)
  - Field-qualified keyword query (text_en:, category:, country:)
  - AND / OR conditions
  - keyword field exact match
  - compound queries (keyword + full-text)
  - wildcard search
  - phrase search
  - NOT condition
  - limit parameter
  - returns list[SearchResult] with correct types
  - input validation (limit < 1, non-string query)
  - closed engine raises JavaSearchError

Notes:
  - auto_analyze=False, lang="en" → full-text field is "text_en"
  - Lucene query uses text_en:Kyoto (not body:Kyoto)
  - Bare term "Kyoto" also works (searches default field)
  - searchLucene has no filters overload; field conditions must be in the query string
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from nlp4j_local_search import SearchEngine
from nlp4j_local_search.errors import InvalidDocumentError, JavaSearchError
from nlp4j_local_search.result import SearchResult

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
    """SearchEngine loaded with DOCS, auto_analyze=False, lang='en'.

    Full-text field: text_en (Lucene internal field name)
    keyword fields:  category, country
    """
    with SearchEngine("en", auto_analyze=False) as eng:
        for doc in DOCS:
            eng.add_json(doc)
        eng.commit()
        yield eng


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

def test_returns_list(engine):
    results = engine.search("Kyoto", 10)
    assert isinstance(results, list)


def test_each_result_is_search_result(engine):
    results = engine.search("Kyoto", 10)
    for r in results:
        assert isinstance(r, SearchResult)


def test_result_fields(engine):
    results = engine.search("Kyoto", 10)
    assert len(results) > 0
    for r in results:
        assert isinstance(r.id, str) and r.id != ""
        assert isinstance(r.score, float)


# ---------------------------------------------------------------------------
# Basic queries (bare term, no field prefix)
# ---------------------------------------------------------------------------

def test_bare_term_kyoto(engine):
    results = engine.search("Kyoto", 10)
    ids = {r.id for r in results}
    assert "1" in ids
    assert "4" in ids


def test_bare_term_no_match(engine):
    results = engine.search("ZZZNOMATCHZZ", 10)
    assert results == []


# ---------------------------------------------------------------------------
# Field-qualified full-text queries (text_en: prefix)
# ---------------------------------------------------------------------------

def test_text_en_field_kyoto(engine):
    results = engine.search("text_en:Kyoto", 10)
    ids = {r.id for r in results}
    assert "1" in ids
    assert "4" in ids


def test_text_en_and_condition(engine):
    results = engine.search("text_en:Kyoto AND text_en:historic", 10)
    ids = {r.id for r in results}
    assert ids == {"1"}


def test_text_en_or_condition(engine):
    results = engine.search("text_en:Kyoto OR text_en:Tokyo", 10)
    ids = {r.id for r in results}
    assert "1" in ids
    assert "2" in ids
    assert "4" in ids


# ---------------------------------------------------------------------------
# keyword field exact match
# ---------------------------------------------------------------------------

def test_keyword_field_city(engine):
    results = engine.search("category:city", 10)
    ids = {r.id for r in results}
    assert ids == {"1", "2", "3"}


def test_keyword_field_company(engine):
    results = engine.search("category:company", 10)
    ids = {r.id for r in results}
    assert ids == {"4", "5", "6"}


def test_keyword_field_country_japan(engine):
    results = engine.search("country:Japan", 10)
    ids = {r.id for r in results}
    assert ids == {"1", "2", "4", "5"}


# ---------------------------------------------------------------------------
# Compound queries
# ---------------------------------------------------------------------------

def test_compound_keyword_and_fulltext(engine):
    results = engine.search("category:company AND text_en:Kyoto", 10)
    ids = {r.id for r in results}
    assert ids == {"4"}


def test_compound_two_keyword_fields(engine):
    results = engine.search("category:city AND country:Japan", 10)
    ids = {r.id for r in results}
    assert ids == {"1", "2"}


# ---------------------------------------------------------------------------
# Wildcard
# ---------------------------------------------------------------------------

def test_wildcard_kyo(engine):
    results = engine.search("text_en:Kyo*", 10)
    ids = {r.id for r in results}
    assert "1" in ids
    assert "4" in ids


# ---------------------------------------------------------------------------
# Phrase search
# ---------------------------------------------------------------------------

def test_phrase_search(engine):
    results = engine.search('text_en:"historic city"', 10)
    ids = {r.id for r in results}
    assert ids == {"1"}


# ---------------------------------------------------------------------------
# NOT condition
# ---------------------------------------------------------------------------

def test_not_condition(engine):
    results = engine.search("category:city AND NOT country:Japan", 10)
    ids = {r.id for r in results}
    assert ids == {"3"}


# ---------------------------------------------------------------------------
# limit parameter
# ---------------------------------------------------------------------------

def test_limit_respected(engine):
    # 3 city docs exist; limit=2 must return at most 2
    results = engine.search("category:city", 2)
    assert len(results) <= 2


def test_default_limit_is_10(engine):
    # 6 docs total; default limit=10 covers all
    results = engine.search("category:city OR category:company")
    assert len(results) == 6


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_limit_zero_raises(engine):
    with pytest.raises(InvalidDocumentError):
        engine.search("Kyoto", 0)


def test_limit_negative_raises(engine):
    with pytest.raises(InvalidDocumentError):
        engine.search("Kyoto", -1)


def test_non_string_query_raises(engine):
    with pytest.raises(InvalidDocumentError):
        engine.search(123, 10)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Closed engine
# ---------------------------------------------------------------------------

def test_closed_engine_raises():
    with SearchEngine("en", auto_analyze=False) as eng:
        eng.add("1", "test document")
        eng.commit()

    with pytest.raises(JavaSearchError):
        eng.search("test", 10)
