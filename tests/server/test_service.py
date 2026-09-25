"""tests/server/test_service.py

SearchService のユニットテスト。
SearchEngine をモックして JVM 不要。
"""
import pytest
from unittest.mock import MagicMock, patch
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from nlp4j_local_search.server.models import SearchRequest, SourceFilter
from nlp4j_local_search.server.service import SearchService
from nlp4j_local_search.server.plan import LexicalSearchPlan, VectorSearchPlan


# ---------------------------------------------------------------------------
# SearchResult の簡易モック
# ---------------------------------------------------------------------------

class FakeResult:
    """nlp4j_local_search.result.SearchResult の最小限モック。"""
    def __init__(self, id_, body, score=1.0):
        self.id = id_
        self.body = body
        self.score = score


# ---------------------------------------------------------------------------
# SearchEngine の簡易モック
# ---------------------------------------------------------------------------

def make_engine(
    docs: list[FakeResult] | None = None,
    total: int | None = None,
    field_kinds: dict[str, str] | None = None,
) -> MagicMock:
    """テスト用 SearchEngine モックを作成。"""
    engine = MagicMock()
    docs = docs or []

    engine.search.return_value = docs
    engine.count.return_value = total if total is not None else len(docs)

    if field_kinds:
        def field_kind(field):
            return field_kinds.get(field)
        engine.field_kind.side_effect = field_kind
    else:
        engine.field_kind.return_value = "TEXT"

    engine.fields.return_value = []

    # field_info は存在しない（field_kind フォールバックを使う）
    del engine.field_info
    # hasattr() が False を返すように設定
    engine.__class__ = type("MockEngine", (), {})

    return engine


# ---------------------------------------------------------------------------
# SearchService のフィクスチャ
# ---------------------------------------------------------------------------

def make_service(
    docs=None,
    total=None,
    field_kinds=None,
) -> tuple[SearchService, MagicMock]:
    engine = make_engine(docs=docs, total=total, field_kinds=field_kinds)
    service = SearchService(engine=engine, index_name="test_index")
    return service, engine


# ---------------------------------------------------------------------------
# check_index
# ---------------------------------------------------------------------------

class TestCheckIndex:

    def test_none_passes(self):
        service, _ = make_service()
        service.check_index(None)  # 例外なし

    def test_matching_index_passes(self):
        service, _ = make_service()
        service.check_index("test_index")  # 例外なし

    def test_wrong_index_raises(self):
        service, _ = make_service()
        with pytest.raises(KeyError):
            service.check_index("other_index")


# ---------------------------------------------------------------------------
# _apply_source_filter
# ---------------------------------------------------------------------------

class TestApplySourceFilter:

    def test_none_returns_all(self):
        source = {"a": 1, "b": 2}
        result = SearchService._apply_source_filter(source, None)
        assert result == {"a": 1, "b": 2}

    def test_false_returns_empty(self):
        source = {"a": 1, "b": 2}
        result = SearchService._apply_source_filter(source, False)
        assert result == {}

    def test_list_includes(self):
        source = {"a": 1, "b": 2, "c": 3}
        result = SearchService._apply_source_filter(source, ["a", "c"])
        assert result == {"a": 1, "c": 3}

    def test_source_filter_includes(self):
        source = {"a": 1, "b": 2, "c": 3}
        sf = SourceFilter(includes=["a"])
        result = SearchService._apply_source_filter(source, sf)
        assert result == {"a": 1}

    def test_source_filter_excludes(self):
        source = {"a": 1, "b": 2, "c": 3}
        sf = SourceFilter(excludes=["b"])
        result = SearchService._apply_source_filter(source, sf)
        assert result == {"a": 1, "c": 3}

    def test_source_filter_includes_and_excludes(self):
        source = {"a": 1, "b": 2, "c": 3}
        sf = SourceFilter(includes=["a", "b"], excludes=["b"])
        result = SearchService._apply_source_filter(source, sf)
        assert result == {"a": 1}


# ---------------------------------------------------------------------------
# _body_to_dict
# ---------------------------------------------------------------------------

class TestBodyToDict:

    def test_none(self):
        assert SearchService._body_to_dict(None) == {}

    def test_dict(self):
        d = {"key": "value"}
        assert SearchService._body_to_dict(d) == d

    def test_json_string(self):
        result = SearchService._body_to_dict('{"key": "value"}')
        assert result == {"key": "value"}

    def test_invalid_json_string(self):
        result = SearchService._body_to_dict("not json")
        assert result == {"body": "not json"}

    def test_non_object_json(self):
        result = SearchService._body_to_dict("[1, 2, 3]")
        assert result == {"body": "[1, 2, 3]"}


# ---------------------------------------------------------------------------
# _convert_hit
# ---------------------------------------------------------------------------

class TestConvertHit:

    def setup_method(self):
        self.service, _ = make_service()

    def test_from_fake_result(self):
        result = FakeResult("doc1", "テキスト", score=0.9)
        hit = self.service._convert_hit(result, None)
        assert hit["_id"] == "doc1"
        assert hit["_score"] == pytest.approx(0.9)
        assert hit["_index"] == "test_index"
        assert hit["_source"] == {"body": "テキスト"}

    def test_from_dict(self):
        result = {"_id": "doc2", "_score": 1.5, "_source": {"title": "hello"}}
        hit = self.service._convert_hit(result, None)
        assert hit["_id"] == "doc2"
        assert hit["_score"] == pytest.approx(1.5)
        assert hit["_source"] == {"title": "hello"}

    def test_source_filter_applied(self):
        result = FakeResult("doc3", '{"a": 1, "b": 2}', score=1.0)
        hit = self.service._convert_hit(result, ["a"])
        assert hit["_source"] == {"a": 1}


# ---------------------------------------------------------------------------
# _hits_response
# ---------------------------------------------------------------------------

class TestHitsResponse:

    def setup_method(self):
        self.service, _ = make_service()

    def test_structure(self):
        hits = [
            {"_index": "i", "_id": "1", "_score": 0.8, "_source": {}},
            {"_index": "i", "_id": "2", "_score": 0.5, "_source": {}},
        ]
        resp = self.service._hits_response(hits=hits, total=10)
        assert resp["hits"]["total"]["value"] == 10
        assert resp["hits"]["total"]["relation"] == "eq"
        assert resp["hits"]["max_score"] == pytest.approx(0.8)
        assert len(resp["hits"]["hits"]) == 2

    def test_no_hits(self):
        resp = self.service._hits_response(hits=[], total=0)
        assert resp["hits"]["max_score"] is None

    def test_none_score_ignored(self):
        hits = [{"_index": "i", "_id": "1", "_score": None, "_source": {}}]
        resp = self.service._hits_response(hits=hits, total=1)
        assert resp["hits"]["max_score"] is None


# ---------------------------------------------------------------------------
# search (lexical)
# ---------------------------------------------------------------------------

class TestSearchLexical:

    def test_match_all(self):
        docs = [FakeResult(str(i), f"doc {i}", score=1.0) for i in range(3)]
        service, engine = make_service(docs=docs, total=3)
        req = SearchRequest(size=10)
        resp = service.search(req)

        assert resp["hits"]["total"]["value"] == 3
        assert len(resp["hits"]["hits"]) == 3
        assert "took" in resp
        assert resp["timed_out"] is False
        assert resp["_shards"]["total"] == 1

    def test_pagination(self):
        docs = [FakeResult(str(i), f"doc {i}", score=1.0) for i in range(5)]
        service, engine = make_service(docs=docs, total=5)
        req = SearchRequest.model_validate({"size": 2, "from": 1})
        resp = service.search(req)

        # search() が limit=3(from+size) で呼ばれ、結果の[1:3]が返る
        assert len(resp["hits"]["hits"]) == 2

    def test_size_zero(self):
        service, engine = make_service(docs=[], total=42)
        req = SearchRequest(size=0)
        resp = service.search(req)
        assert resp["hits"]["total"]["value"] == 42
        assert len(resp["hits"]["hits"]) == 0


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------

class TestCount:

    def test_count_all(self):
        service, engine = make_service(total=100)
        resp = service.count(None)
        assert resp["count"] == 100
        assert resp["_shards"]["total"] == 1

    def test_count_with_query(self):
        service, engine = make_service(total=5)
        resp = service.count({"term": {"maker_s": "NISSAN"}})
        assert resp["count"] == 5

    def test_vector_query_raises(self):
        service, engine = make_service(field_kinds={"vector": "VECTOR"})
        with pytest.raises(ValueError, match="VECTOR"):
            service.count({"match": {"vector": "テスト"}})


# ---------------------------------------------------------------------------
# mapping
# ---------------------------------------------------------------------------

class TestMapping:

    def test_empty_fields(self):
        service, engine = make_service()
        engine.fields.return_value = []
        resp = service.mapping()
        assert "test_index" in resp
        assert resp["test_index"]["mappings"]["properties"] == {}

    def test_str_fields(self):
        service, engine = make_service()
        engine.fields.return_value = ["text_ja", "maker_s"]
        engine.field_kind.side_effect = lambda f: {"text_ja": "TEXT", "maker_s": "KEYWORD"}.get(f)
        resp = service.mapping()
        props = resp["test_index"]["mappings"]["properties"]
        assert props["text_ja"]["type"] == "text"
        assert props["maker_s"]["type"] == "keyword"

    def test_vector_field(self):
        service, engine = make_service()
        engine.fields.return_value = [
            {"name": "vector", "type": "VECTOR", "dimension": 1024, "similarity": "cosine", "model": "e5-large"}
        ]
        resp = service.mapping()
        props = resp["test_index"]["mappings"]["properties"]
        assert props["vector"]["type"] == "dense_vector"
        assert props["vector"]["dims"] == 1024
        assert props["vector"]["similarity"] == "cosine"
        assert props["vector"]["nlp4j_model"] == "e5-large"


# ---------------------------------------------------------------------------
# field_type フォールバック
# ---------------------------------------------------------------------------

class TestFieldType:

    def test_field_kind_fallback(self):
        service, engine = make_service(field_kinds={"text_ja": "TEXT"})
        ft = service.field_type("text_ja")
        assert ft == "TEXT"

    def test_unknown_field_raises(self):
        service, engine = make_service()
        engine.field_kind.return_value = None
        with pytest.raises(ValueError, match="Unknown field"):
            service.field_type("nonexistent_field")
