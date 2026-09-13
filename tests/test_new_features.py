"""Tests for the updated features in SearchEngine:
  - default_search_fields()
  - vector_dimension restored from Java getVectorDimension()
  - time_zone in constructor
  - save_index_to() and loadIndexFrom via index_dir
  - aggregate() using aggregate_json()
  - save_index_to() marks engine as closed
  - _RESERVED_FIELDS validation
  - add(id, text, fields=...) text field unification
"""
import os
import shutil
import tempfile
import pytest

from nlp4j_local_search import SearchEngine
from nlp4j_local_search.errors import InvalidDocumentError, JavaSearchError


def test_default_search_fields():
    with SearchEngine("ja") as engine_ja:
        assert engine_ja.default_search_fields() == ["text_ja", "text", "body"]

    with SearchEngine("en") as engine_en:
        assert engine_en.default_search_fields() == ["text_en", "text", "body"]


def test_vector_dimension_from_java():
    with SearchEngine("ja") as engine_no_vec:
        assert engine_no_vec.vector_dimension == 0

    with SearchEngine("ja", vector_dimension=3) as engine:
        assert engine.vector_dimension == 3
        # array or any Sequence[float]
        import array
        vec_arr = array.array('f', [1.0, 0.0, 0.0])
        engine.add("1", vec_arr)
        engine.commit()
        results = engine.search_vector(vec_arr, 10)
        assert len(results) == 1
        assert results[0].id == "1"


def test_reserved_fields():
    with SearchEngine("en") as engine:
        # Cannot use text, text_ja, text_en, data, id, body, vector in fields
        for reserved in ["id", "body", "text", "text_ja", "text_en", "vector", "data"]:
            with pytest.raises(InvalidDocumentError):
                engine.add("1", "Hello", fields={reserved: "value"})


def test_add_fields_text_unification():
    with SearchEngine("en") as engine:
        engine.add("1", "Kyoto is historic")
        engine.add("2", "Kyoto is ancient", fields={"category": "city"})
        engine.commit()

        # Both documents should be found via text_en:Kyoto and category:city works on doc 2
        results_text_en = engine.search("text_en:Kyoto", 10)
        ids_text_en = {r.id for r in results_text_en}
        assert ids_text_en == {"1", "2"}

        results_cat = engine.search("category:city", 10)
        assert len(results_cat) == 1
        assert results_cat[0].id == "2"


def test_aggregate_high_level():
    with SearchEngine("en") as engine:
        engine.add("1", "Kyoto is in Japan", fields={"category": "city", "country": "Japan"})
        engine.add("2", "Tokyo is in Japan", fields={"category": "city", "country": "Japan"})
        engine.add("3", "Sony is in Japan", fields={"category": "company", "country": "Japan"})
        engine.add("4", "Paris is in France", fields={"category": "city", "country": "France"})
        engine.commit()

        # 1. aggregate(field, size)
        agg1 = engine.aggregate("category", size=10)
        buckets1 = {b["key"]: b["doc_count"] for b in agg1["aggregations"]["category"]["buckets"]}
        assert buckets1["city"] == 3
        assert buckets1["company"] == 1

        # 2. aggregate(field, query=..., size=...)
        agg2 = engine.aggregate("category", query="text_en:Kyoto", size=10)
        buckets2 = {b["key"]: b["doc_count"] for b in agg2["aggregations"]["category"]["buckets"]}
        assert buckets2 == {"city": 1}

        # 3. aggregate(field, query=..., filters=..., size=...)
        agg3 = engine.aggregate("category", query="Japan", filters={"country": "Japan"}, size=10)
        buckets3 = {b["key"]: b["doc_count"] for b in agg3["aggregations"]["category"]["buckets"]}
        assert buckets3["city"] == 2
        assert buckets3["company"] == 1

        # 4. aggregate on non-aggregatable field raises error
        with pytest.raises(JavaSearchError):
            engine.aggregate("text_en", size=10)


def test_save_index_to_closes_engine():
    temp_dir = tempfile.mkdtemp(prefix="localsearch_test_close_")
    try:
        engine = SearchEngine("en")
        engine.add("1", "Hello")
        engine.commit()
        engine.save_index_to(temp_dir)

        assert engine._closed is True
        with pytest.raises(JavaSearchError, match="already closed"):
            engine.search("Hello")

        # closing again should be safe
        engine.close()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_time_zone_support():
    with SearchEngine("ja", time_zone="Asia/Tokyo") as engine:
        engine.add("1", "テスト")
        engine.commit()
        results = engine.search("テスト", 10)
        assert len(results) == 1


def test_save_and_load_index_dir():
    temp_dir = tempfile.mkdtemp(prefix="localsearch_test_save_load_")
    try:
        # Create and save index with vector
        with SearchEngine("en", vector_dimension=3) as engine:
            engine.add("1", [1.0, 0.0, 0.0], fields={"category": "tech"})
            engine.add("2", "Kyoto is historic", fields={"category": "city"})
            engine.commit()
            engine.save_index_to(temp_dir)

        # Load from disk with index_dir
        with SearchEngine("en", index_dir=temp_dir) as loaded:
            assert loaded.vector_dimension == 3

            # Search text
            text_res = loaded.search("Kyoto", 10)
            assert len(text_res) == 1
            assert text_res[0].id == "2"

            # Search vector
            vec_res = loaded.search_vector([1.0, 0.0, 0.0], 10)
            assert len(vec_res) >= 1
            assert vec_res[0].id == "1"

            # Search field
            cat_res = loaded.search("category:tech", 10)
            assert len(cat_res) == 1
            assert cat_res[0].id == "1"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
