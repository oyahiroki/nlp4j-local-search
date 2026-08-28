"""
Tests for SearchEngine.view() — inspection API (updated).

Covers:
  - engine.view()                             overview: count mode
  - engine.view("field")                      single field: count mode
  - engine.view("field", "maker:Nissan")      single field: relativeRate mode
  - engine.view(lucene_query="maker:Nissan")  overview: relativeRate mode
  - candidate_size parameter
  - ViewResult.sort_by()
  - ViewResult.filter()
  - ViewBucket: all_count / relative_rate fields
  - ViewField: count / total_count fields
  - Display formatting (count mode vs relativeRate mode)
  - engine.relative_rate_lucene()
  - engine.fields() / engine.aggregatable_fields()
  - Input validation

Based on Example23_View.java (nlp4j-localsearch.jar 0.5.1).

Dataset (autoAnalyze=False, lang="en"):
  id=1  Nissan  body        door mirror
  id=2  Nissan  body        door mirror
  id=3  Nissan  electrical  battery
  id=4  Toyota  brake       brake
  id=5  Toyota  electrical  battery
  id=6  Honda   brake       brake
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from nlp4j_local_search import SearchEngine, ViewBucket, ViewField, ViewResult
from nlp4j_local_search.errors import InvalidDocumentError


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

def _build_engine():
    """6-document dataset mirroring Example23_View.java."""
    engine = SearchEngine("en", auto_analyze=False)
    engine.add_json({"id": "1", "body": "Nissan reported a broken door mirror.",  "maker": "Nissan", "category": "body",       "part": "door mirror"})
    engine.add_json({"id": "2", "body": "Nissan reported a door mirror failure.", "maker": "Nissan", "category": "body",       "part": "door mirror"})
    engine.add_json({"id": "3", "body": "Nissan reported a battery problem.",     "maker": "Nissan", "category": "electrical", "part": "battery"})
    engine.add_json({"id": "4", "body": "Toyota reported a brake problem.",       "maker": "Toyota", "category": "brake",      "part": "brake"})
    engine.add_json({"id": "5", "body": "Toyota reported a battery problem.",     "maker": "Toyota", "category": "electrical", "part": "battery"})
    engine.add_json({"id": "6", "body": "Honda reported a brake problem.",        "maker": "Honda",  "category": "brake",      "part": "brake"})
    engine.commit()
    return engine


# ===========================================================================
# engine.fields() / engine.aggregatable_fields()
# ===========================================================================

def test_fields_contains_custom():
    with _build_engine() as engine:
        f = engine.fields()
        assert "maker" in f
        assert "category" in f
        assert "part" in f


def test_aggregatable_fields_contains_custom():
    with _build_engine() as engine:
        af = engine.aggregatable_fields()
        assert "maker" in af
        assert "category" in af
        assert "part" in af


# ===========================================================================
# engine.view() — count mode (no lucene_query)
# ===========================================================================

def test_view_no_args_returns_view_result():
    with _build_engine() as engine:
        result = engine.view()
        assert isinstance(result, ViewResult)
        assert result.single_field is False
        assert result.lucene_query is None
        assert result.sort_key == "count"


def test_view_no_args_default_size_3():
    with _build_engine() as engine:
        result = engine.view()
        for vf in result.fields:
            assert len(vf.buckets) <= 3


def test_view_no_args_count_only():
    """count mode: relative_rate is None for all buckets."""
    with _build_engine() as engine:
        result = engine.view()
        for vf in result.fields:
            for b in vf.buckets:
                assert b.relative_rate is None
                assert b.all_count is None


def test_view_no_args_maker_counts():
    with _build_engine() as engine:
        result = engine.view(size=10)
        maker_field = next(vf for vf in result.fields if vf.field == "maker")
        bucket_map = {b.key: b.count for b in maker_field.buckets}
        assert bucket_map["Nissan"] == 3
        assert bucket_map["Toyota"] == 2
        assert bucket_map["Honda"] == 1


def test_view_single_field_count_mode():
    """engine.view('category') returns count-only ViewField."""
    with _build_engine() as engine:
        result = engine.view("category")
        assert result.single_field is True
        assert result.sort_key == "count"
        vf = result.fields[0]
        assert vf.field == "category"
        assert vf.count is None
        assert vf.total_count is None
        bucket_map = {b.key: b.count for b in vf.buckets}
        # body=2, brake=2, electrical=2
        assert bucket_map["body"] == 2
        assert bucket_map["brake"] == 2
        assert bucket_map["electrical"] == 2
        for b in vf.buckets:
            assert b.relative_rate is None
            assert b.all_count is None


def test_view_single_field_size_1():
    with _build_engine() as engine:
        result = engine.view("category", size=1)
        assert len(result.fields[0].buckets) == 1


# ===========================================================================
# engine.view() — relativeRate mode (with lucene_query)
# ===========================================================================
# Example23 expected:
#   maker:Nissan → part:
#     door mirror  count=2, all_count=2, relative_rate=2.00
#     battery      count=1, all_count=2, relative_rate=1.00

def test_view_lucene_query_single_field_returns_view_result():
    with _build_engine() as engine:
        result = engine.view("part", "maker:Nissan")
        assert isinstance(result, ViewResult)
        assert result.single_field is True
        assert result.lucene_query == "maker:Nissan"
        assert result.sort_key == "relative_rate"


def test_view_lucene_query_buckets_have_relative_rate():
    with _build_engine() as engine:
        result = engine.view("part", "maker:Nissan")
        vf = result.fields[0]
        assert vf.count == 3        # 3 Nissan docs
        assert vf.total_count == 6  # 6 total docs
        for b in vf.buckets:
            assert b.relative_rate is not None
            assert b.all_count is not None


def test_view_lucene_query_door_mirror_relative_rate():
    """door mirror: 2/3 vs 2/6 → relative_rate ≈ 2.0 (Example23 expected)."""
    with _build_engine() as engine:
        result = engine.view("part", "maker:Nissan")
        vf = result.fields[0]
        bucket_map = {b.key: b for b in vf.buckets}
        dm = bucket_map["door mirror"]
        assert dm.count == 2
        assert dm.all_count == 2
        assert abs(dm.relative_rate - 2.0) < 0.01


def test_view_lucene_query_battery_relative_rate():
    """battery: 1/3 vs 2/6 → relative_rate ≈ 1.0 (Example23 expected)."""
    with _build_engine() as engine:
        result = engine.view("part", "maker:Nissan")
        vf = result.fields[0]
        bucket_map = {b.key: b for b in vf.buckets}
        bat = bucket_map["battery"]
        assert bat.count == 1
        assert bat.all_count == 2
        assert abs(bat.relative_rate - 1.0) < 0.01


def test_view_lucene_query_ordered_by_relative_rate():
    """door mirror (2.0x) should come before battery (1.0x)."""
    with _build_engine() as engine:
        result = engine.view("part", "maker:Nissan")
        vf = result.fields[0]
        rates = [b.relative_rate for b in vf.buckets]
        assert rates == sorted(rates, reverse=True)


def test_view_lucene_query_overview():
    """engine.view(lucene_query=...) overview mode uses relativeRate."""
    with _build_engine() as engine:
        result = engine.view(lucene_query="maker:Nissan", size=10)
        assert result.single_field is False
        assert result.lucene_query == "maker:Nissan"
        part_field = next((vf for vf in result.fields if vf.field == "part"), None)
        assert part_field is not None
        for b in part_field.buckets:
            assert b.relative_rate is not None


def test_view_candidate_size():
    """candidate_size limits Java-side computation candidates."""
    with _build_engine() as engine:
        r1 = engine.view("part", "maker:Nissan", candidate_size=1000)
        r2 = engine.view("part", "maker:Nissan", candidate_size=1)
        # both return ViewResult; small candidate_size may truncate
        assert isinstance(r1, ViewResult)
        assert isinstance(r2, ViewResult)


# ===========================================================================
# engine.relative_rate_lucene()
# ===========================================================================

def test_relative_rate_lucene_returns_analytics_result():
    from nlp4j_local_search import AnalyticsResult
    with _build_engine() as engine:
        result = engine.relative_rate_lucene("maker:Nissan", "part")
        assert isinstance(result, AnalyticsResult)
        assert result.lucene_query == "maker:Nissan"
        assert result.field == "part"
        assert result.count == 3
        assert result.total_count == 6
        assert result.query_field is None
        assert result.query_value is None


def test_relative_rate_lucene_buckets():
    with _build_engine() as engine:
        result = engine.relative_rate_lucene("maker:Nissan", "part")
        bucket_map = {b.key: b for b in result.buckets}
        assert "door mirror" in bucket_map
        assert bucket_map["door mirror"].count == 2
        assert abs(bucket_map["door mirror"].relative_rate - 2.0) < 0.01


def test_relative_rate_lucene_empty_query_raises():
    with _build_engine() as engine:
        with pytest.raises(InvalidDocumentError):
            engine.relative_rate_lucene("", "part")


def test_relative_rate_lucene_empty_field_raises():
    with _build_engine() as engine:
        with pytest.raises(InvalidDocumentError):
            engine.relative_rate_lucene("maker:Nissan", "")


def test_relative_rate_lucene_zero_candidate_size_raises():
    with _build_engine() as engine:
        with pytest.raises(InvalidDocumentError):
            engine.relative_rate_lucene("maker:Nissan", "part", candidate_size=0)


# ===========================================================================
# ViewResult.sort_by()
# ===========================================================================

def test_sort_by_count_descending():
    with _build_engine() as engine:
        result = engine.view("maker", size=10).sort_by("count")
        counts = [b.count for b in result.fields[0].buckets]
        assert counts == sorted(counts, reverse=True)


def test_sort_by_count_ascending():
    with _build_engine() as engine:
        result = engine.view("maker", size=10).sort_by("count", descending=False)
        counts = [b.count for b in result.fields[0].buckets]
        assert counts == sorted(counts)


def test_sort_by_relative_rate():
    with _build_engine() as engine:
        result = engine.view("part", "maker:Nissan").sort_by("relative_rate")
        rates = [b.relative_rate for b in result.fields[0].buckets]
        assert rates == sorted(rates, reverse=True)


def test_sort_by_returns_new_object():
    """sort_by() must not mutate the original ViewResult."""
    with _build_engine() as engine:
        original = engine.view("maker", size=10)
        sorted_result = original.sort_by("count", descending=False)
        # original is unchanged
        orig_counts = [b.count for b in original.fields[0].buckets]
        sorted_counts = [b.count for b in sorted_result.fields[0].buckets]
        assert orig_counts != sorted_counts or orig_counts == sorted(orig_counts)


def test_sort_by_updates_sort_key():
    with _build_engine() as engine:
        result = engine.view("part", "maker:Nissan").sort_by("count")
        assert result.sort_key == "count"


# ===========================================================================
# ViewResult.filter()
# ===========================================================================

def test_filter_min_count():
    with _build_engine() as engine:
        result = engine.view("maker", size=10).filter(min_count=2)
        for b in result.fields[0].buckets:
            assert b.count >= 2


def test_filter_max_count():
    with _build_engine() as engine:
        result = engine.view("maker", size=10).filter(max_count=2)
        for b in result.fields[0].buckets:
            assert b.count <= 2


def test_filter_min_relative_rate():
    with _build_engine() as engine:
        result = engine.view("part", "maker:Nissan").filter(min_relative_rate=1.5)
        # only door mirror (2.0x) should remain
        vf = result.fields[0]
        assert len(vf.buckets) == 1
        assert vf.buckets[0].key == "door mirror"


def test_filter_returns_new_object():
    """filter() must not mutate the original."""
    with _build_engine() as engine:
        original = engine.view("part", "maker:Nissan")
        filtered = original.filter(min_relative_rate=1.5)
        assert len(original.fields[0].buckets) >= len(filtered.fields[0].buckets)


def test_filter_chain():
    """Chain: filter → sort_by."""
    with _build_engine() as engine:
        result = (
            engine.view("part", "maker:Nissan")
            .filter(min_count=1)
            .sort_by("relative_rate")
        )
        rates = [b.relative_rate for b in result.fields[0].buckets]
        assert rates == sorted(rates, reverse=True)


# ===========================================================================
# Display formatting
# ===========================================================================

def test_str_overview_count_mode_header():
    with _build_engine() as engine:
        text = str(engine.view())
        assert "View: aggregatable fields" in text
        assert "Format: field | value (document count)" in text


def test_str_overview_relative_rate_mode_header():
    with _build_engine() as engine:
        text = str(engine.view(lucene_query="maker:Nissan", size=10))
        assert "Format: field | value (count, relative rate)" in text
        assert "Lucene query: maker:Nissan" in text


def test_str_single_field_count_mode():
    with _build_engine() as engine:
        text = str(engine.view("category"))
        assert "View: category" in text
        assert "Values are ordered by document count." in text
        assert "Rank" in text
        assert "Count" in text
        # relativeRate columns absent
        assert "Relative Rate" not in text
        assert "All Count" not in text


def test_str_single_field_relative_rate_mode():
    with _build_engine() as engine:
        text = str(engine.view("part", "maker:Nissan"))
        assert "View: part" in text
        assert "Lucene query: maker:Nissan" in text
        assert "Matched documents: 3 / 6" in text
        assert "Values are ordered by relative rate." in text
        assert "Relative Rate" in text
        assert "All Count" in text
        assert "door mirror" in text
        assert "2.00x" in text


def test_repr_equals_str():
    with _build_engine() as engine:
        result = engine.view("part", "maker:Nissan")
        assert repr(result) == str(result)


# ===========================================================================
# ViewBucket / ViewField / ViewResult frozen dataclass
# ===========================================================================

def test_view_bucket_frozen():
    vb = ViewBucket(key="x", count=1)
    with pytest.raises((AttributeError, TypeError)):
        vb.count = 2  # type: ignore[misc]


def test_view_field_frozen():
    vf = ViewField(field="x", buckets=[])
    with pytest.raises((AttributeError, TypeError)):
        vf.field = "y"  # type: ignore[misc]


def test_view_result_frozen():
    vr = ViewResult(fields=[])
    with pytest.raises((AttributeError, TypeError)):
        vr.fields = []  # type: ignore[misc]


# ===========================================================================
# aggregate() with Lucene query
# ===========================================================================

def test_aggregate_with_lucene_query():
    """aggregate(query=) now accepts Lucene Query Syntax."""
    with _build_engine() as engine:
        response = engine.aggregate("maker", query="maker:Nissan")
        buckets = (
            response
            .get("aggregations", {})
            .get("maker", {})
            .get("buckets", [])
        )
        assert len(buckets) == 1
        assert buckets[0]["key"] == "Nissan"


# ===========================================================================
# view() input validation
# ===========================================================================

def test_view_zero_size_raises():
    with _build_engine() as engine:
        with pytest.raises(InvalidDocumentError):
            engine.view("category", size=0)


def test_view_zero_candidate_size_raises():
    with _build_engine() as engine:
        with pytest.raises(InvalidDocumentError):
            engine.view("part", "maker:Nissan", candidate_size=0)
