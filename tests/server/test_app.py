"""tests/server/test_app.py

FastAPI エンドポイントの統合テスト。
httpx + TestClient を使用。SearchEngine はモック。
JVM 不要。
"""
import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

# fastapi / httpx がインストールされていない場合はスキップ
pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from nlp4j_local_search.server.app import create_app
from nlp4j_local_search.server.service import ServerConfig


# ---------------------------------------------------------------------------
# 共通ヘルパー
# ---------------------------------------------------------------------------

class FakeResult:
    def __init__(self, id_, body, score=1.0):
        self.id = id_
        self.body = body
        self.score = score


@contextmanager
def app_client(docs=None, total=None, field_kinds=None):
    """
    コンテキストマネージャとして使う TestClient を返す。
    SearchEngine のコンストラクタをパッチして JVM を回避。
    with app_client(...) as (client, engine): の形で使う。
    """
    docs = docs or []
    total = total if total is not None else len(docs)

    engine_mock = MagicMock(spec=[])
    engine_mock.search = MagicMock(return_value=docs)
    engine_mock.count = MagicMock(return_value=total)
    engine_mock.fields = MagicMock(return_value=["text_ja", "maker_s"])
    engine_mock.close = MagicMock()

    if field_kinds:
        engine_mock.field_kind = MagicMock(side_effect=lambda f: field_kinds.get(f, "TEXT"))
    else:
        engine_mock.field_kind = MagicMock(return_value="TEXT")

    config = ServerConfig(lang="en", index_name="test_index")

    with patch(
        "nlp4j_local_search.server.app.SearchEngine",
        return_value=engine_mock,
    ):
        app = create_app(config)
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client, engine_mock


# ---------------------------------------------------------------------------
# root
# ---------------------------------------------------------------------------

class TestRootEndpoint:

    def test_get_root(self):
        with app_client() as (client, _):
            resp = client.get("/")
            assert resp.status_code == 200
            body = resp.json()
            assert body["name"] == "nlp4j-local-search"
            assert "version" in body
            assert "tagline" in body


# ---------------------------------------------------------------------------
# mapping
# ---------------------------------------------------------------------------

class TestMappingEndpoint:

    def test_get_mapping(self):
        with app_client() as (client, engine):
            engine.fields.return_value = ["text_ja"]
            engine.field_kind.return_value = "TEXT"
            resp = client.get("/test_index/_mapping")
            assert resp.status_code == 200
            body = resp.json()
            assert "test_index" in body

    def test_wrong_index_returns_404(self):
        with app_client() as (client, _):
            resp = client.get("/wrong_index/_mapping")
            assert resp.status_code == 404
            detail = resp.json()["detail"]
            assert detail["type"] == "index_not_found_exception"


# ---------------------------------------------------------------------------
# search GET
# ---------------------------------------------------------------------------

class TestSearchGetEndpoint:

    def test_empty_query(self):
        docs = [FakeResult("1", "東京都", 1.0)]
        with app_client(docs=docs, total=1) as (client, engine):
            resp = client.get("/test_index/_search")
            assert resp.status_code == 200
            body = resp.json()
            assert body["hits"]["total"]["value"] == 1
            assert len(body["hits"]["hits"]) == 1

    def test_q_param(self):
        docs = [FakeResult("1", "東京都", 1.0)]
        with app_client(docs=docs, total=1) as (client, engine):
            resp = client.get("/test_index/_search?q=東京")
            assert resp.status_code == 200
            engine.search.assert_called()

    def test_size_param(self):
        with app_client(docs=[], total=0) as (client, engine):
            resp = client.get("/test_index/_search?size=5")
            assert resp.status_code == 200

    def test_wrong_index_404(self):
        with app_client() as (client, _):
            resp = client.get("/wrong/_search")
            assert resp.status_code == 404


# ---------------------------------------------------------------------------
# search POST
# ---------------------------------------------------------------------------

class TestSearchPostEndpoint:

    def test_match_all(self):
        docs = [FakeResult("1", "テキスト", 1.0)]
        with app_client(docs=docs, total=1) as (client, engine):
            resp = client.post(
                "/test_index/_search",
                json={"query": {"match_all": {}}, "size": 10},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["hits"]["total"]["value"] == 1

    def test_term_query(self):
        docs = [FakeResult("1", "テキスト", 0.8)]
        with app_client(docs=docs, total=1) as (client, engine):
            resp = client.post(
                "/test_index/_search",
                json={"query": {"term": {"maker_s": "NISSAN"}}, "size": 5},
            )
            assert resp.status_code == 200
            args = engine.search.call_args
            assert args is not None
            lucene_q = args[0][0]
            assert "NISSAN" in lucene_q

    def test_invalid_query_returns_400(self):
        with app_client() as (client, _):
            resp = client.post(
                "/test_index/_search",
                json={"query": {"bad field!": "value"}},
            )
            assert resp.status_code == 400
            detail = resp.json()["detail"]
            assert "type" in detail

    def test_unsupported_query_returns_400(self):
        with app_client() as (client, _):
            resp = client.post(
                "/test_index/_search",
                json={"query": {"fuzzy": {"text_ja": "test"}}},
            )
            assert resp.status_code == 400
            detail = resp.json()["detail"]
            assert detail["type"] == "unsupported_query_exception"

    def test_size_zero(self):
        with app_client(total=42) as (client, engine):
            resp = client.post(
                "/test_index/_search",
                json={"size": 0},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["hits"]["total"]["value"] == 42
            assert body["hits"]["hits"] == []

    def test_source_filter_list(self):
        docs = [FakeResult("1", '{"title": "T", "body": "B"}', 1.0)]
        with app_client(docs=docs, total=1) as (client, engine):
            resp = client.post(
                "/test_index/_search",
                json={"query": {"match_all": {}}, "_source": ["title"]},
            )
            assert resp.status_code == 200
            body = resp.json()
            hit_source = body["hits"]["hits"][0]["_source"]
            assert "title" in hit_source
            assert "body" not in hit_source

    def test_range_query(self):
        docs = [FakeResult("1", "doc", 1.0)]
        with app_client(docs=docs, total=1) as (client, engine):
            resp = client.post(
                "/test_index/_search",
                json={"query": {"range": {"year": {"gte": 2020, "lte": 2025}}}},
            )
            assert resp.status_code == 200
            args = engine.search.call_args
            lucene_q = args[0][0]
            assert "year:[2020 TO 2025]" == lucene_q

    def test_bool_must(self):
        docs = [FakeResult("1", "doc", 1.0)]
        with app_client(docs=docs, total=1) as (client, engine):
            resp = client.post(
                "/test_index/_search",
                json={
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"maker_s": "NISSAN"}},
                            ]
                        }
                    }
                },
            )
            assert resp.status_code == 200
            args = engine.search.call_args
            lucene_q = args[0][0]
            assert "NISSAN" in lucene_q

    def test_wrong_index_404(self):
        with app_client() as (client, _):
            resp = client.post("/wrong/_search", json={})
            assert resp.status_code == 404


# ---------------------------------------------------------------------------
# count GET
# ---------------------------------------------------------------------------

class TestCountGetEndpoint:

    def test_count_all(self):
        with app_client(total=100) as (client, engine):
            resp = client.get("/test_index/_count")
            assert resp.status_code == 200
            body = resp.json()
            assert body["count"] == 100
            assert body["_shards"]["total"] == 1

    def test_count_with_q(self):
        with app_client(total=5) as (client, engine):
            resp = client.get("/test_index/_count?q=maker_s:NISSAN")
            assert resp.status_code == 200
            body = resp.json()
            assert body["count"] == 5

    def test_wrong_index_404(self):
        with app_client() as (client, _):
            resp = client.get("/wrong/_count")
            assert resp.status_code == 404


# ---------------------------------------------------------------------------
# count POST
# ---------------------------------------------------------------------------

class TestCountPostEndpoint:

    def test_count_with_term(self):
        with app_client(total=7) as (client, engine):
            resp = client.post(
                "/test_index/_count",
                json={"query": {"term": {"maker_s": "TOYOTA"}}},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["count"] == 7

    def test_count_no_query(self):
        with app_client(total=100) as (client, engine):
            resp = client.post("/test_index/_count", json={})
            assert resp.status_code == 200
            assert resp.json()["count"] == 100

    def test_wrong_index_404(self):
        with app_client() as (client, _):
            resp = client.post("/wrong/_count", json={})
            assert resp.status_code == 404
