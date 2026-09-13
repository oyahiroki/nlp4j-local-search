"""Tests for SearchEngine.search()

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
  - filters= keyword argument (non-scoring structured filter)
  - returns list[SearchResult] with correct types
  - input validation (limit < 1, non-string query)
  - closed engine raises JavaSearchError

Notes:
  - auto_analyze=False, lang="en" → full-text field is "text_en"
  - Lucene query uses text_en:Kyoto (not body:Kyoto)
  - Bare term "Kyoto" also works (searches default field)
  - filters= maps to Java search(String, int, Map) overload
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
    {"id": "1", "text_en": "Kyoto is a historic city in Japan.",
     "category": "city",    "country": "Japan"},
    {"id": "2", "text_en": "Tokyo is the capital city of Japan.",
     "category": "city",    "country": "Japan"},
    {"id": "3", "text_en": "Paris is the capital city of France.",
     "category": "city",    "country": "France"},
    {"id": "4", "text_en": "Nintendo is headquartered in Kyoto, Japan.",
     "category": "company", "country": "Japan"},
    {"id": "5", "text_en": "Sony is a Japanese multinational company.",
     "category": "company", "country": "Japan"},
    {"id": "6", "text_en": "Microsoft is headquartered in Redmond, USA.",
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


def test_empty_query_raises(engine):
    """search('') raises InvalidDocumentError regardless of filters."""
    with pytest.raises(InvalidDocumentError, match="non-empty"):
        engine.search("")


def test_empty_query_with_filters_also_raises(engine):
    """search('', filters=...) also raises — Java rejects blank queries."""
    with pytest.raises(InvalidDocumentError, match="non-empty"):
        engine.search("", filters={"category": "city"})


def test_whitespace_only_query_raises(engine):
    """search('   ') raises InvalidDocumentError."""
    with pytest.raises(InvalidDocumentError, match="non-empty"):
        engine.search("   ")


def test_filter_only_use_match_all(engine):
    """Filter-only search should use '*:*' explicitly."""
    results = engine.search("*:*", filters={"category": "city"})
    ids = {r.id for r in results}
    assert ids == {"1", "2", "3"}


# ---------------------------------------------------------------------------
# Closed engine
# ---------------------------------------------------------------------------

def test_closed_engine_raises():
    with SearchEngine("en", auto_analyze=False) as eng:
        eng.add("1", "test document")
        eng.commit()

    with pytest.raises(JavaSearchError):
        eng.search("test", 10)


# ---------------------------------------------------------------------------
# filters= keyword argument
# ---------------------------------------------------------------------------

def test_filters_single_field(engine):
    """filters={"category": "company"} restricts to company docs only."""
    results = engine.search("Kyoto", filters={"category": "company"})
    ids = {r.id for r in results}
    # id=4 (Nintendo, Kyoto, company) should match; id=1 (city) should not
    assert "4" in ids
    assert "1" not in ids


def test_filters_no_match(engine):
    """filters that match no documents returns empty list."""
    results = engine.search("Kyoto", filters={"category": "nonexistent"})
    assert results == []


def test_filters_combined_with_lucene_field(engine):
    """filters combined with Lucene text query."""
    results = engine.search("text_en:Japan", filters={"category": "city"})
    ids = {r.id for r in results}
    # Only Japan city docs: id=1 (Kyoto/city), id=2 (Tokyo/city)
    assert ids.issubset({"1", "2", "3"})
    assert "5" not in ids  # Sony (company) excluded by filter


def test_filters_empty_dict_treated_as_no_filter(engine):
    """Empty filters={} should behave like no filter."""
    results_no_filter = engine.search("Kyoto", 10)
    results_empty_filter = engine.search("Kyoto", 10, filters={})
    assert {r.id for r in results_no_filter} == {r.id for r in results_empty_filter}
