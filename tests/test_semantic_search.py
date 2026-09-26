"""
Tests for embedding=True / search_semantic() — Phase 1.

All tests use FakeEmbedding (no ML model required) per the design spec
in kaiwa20260926-1543.md.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from nlp4j_local_search import SearchEngine
from nlp4j_local_search.errors import InvalidDocumentError


# ---------------------------------------------------------------------------
# Fake embedding provider (no model download, CI-safe)
# ---------------------------------------------------------------------------

class FakeEmbedding:
    """3-D provider: embed_query always returns [1.0, 0.0, 0.0]."""

    @property
    def dimension(self) -> int:
        return 3

    def embed_query(self, text: str):
        return [1.0, 0.0, 0.0]

    def embed_documents(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]


# ---------------------------------------------------------------------------
# 1. 従来互換: embedding なしでも search() は動作する
# ---------------------------------------------------------------------------

def test_legacy_text_search_still_works():
    """embedding なし SearchEngine でテキスト検索が動作すること。"""
    with SearchEngine("ja") as engine:
        engine.add("1", "京都です")
        engine.commit()
        results = engine.search("京都")
        assert results


# ---------------------------------------------------------------------------
# 2. embedding=True でエンジンを作ると embedding が設定される
#    (E5 モデルは実際にはロードしないので FakeEmbedding で代替検証)
# ---------------------------------------------------------------------------

def test_embedding_false_sets_none():
    """embedding=False (default) では engine.embedding が None になること。"""
    with SearchEngine("ja") as engine:
        assert engine.embedding is None


def test_embedding_none_sets_none():
    """embedding=None でも engine.embedding が None になること。"""
    with SearchEngine("ja", embedding=None) as engine:
        assert engine.embedding is None


def test_embedding_provider_is_stored():
    """EmbeddingProvider インスタンスを渡すと engine.embedding に格納されること。"""
    provider = FakeEmbedding()
    with SearchEngine("ja", embedding=provider) as engine:
        assert engine.embedding is provider


def test_embedding_sets_vector_dimension():
    """embedding= 指定時に vector_dimension が provider.dimension と一致すること。"""
    provider = FakeEmbedding()
    with SearchEngine("ja", embedding=provider) as engine:
        assert engine.vector_dimension == provider.dimension


# ---------------------------------------------------------------------------
# 3. 自動 Embedding add
# ---------------------------------------------------------------------------

def test_add_with_embedding_indexes_document():
    """embedding 設定時に add(id, text) でドキュメントが登録されること。"""
    provider = FakeEmbedding()
    with SearchEngine("ja", embedding=provider) as engine:
        engine.add("1", "京都は日本の古都です")
        engine.commit()
        assert engine.count() == 1


def test_add_multiple_with_embedding():
    """複数ドキュメントを add したときの count が一致すること。"""
    provider = FakeEmbedding()
    with SearchEngine("ja", embedding=provider) as engine:
        engine.add("1", "京都は日本の古都です")
        engine.add("2", "東京は日本最大の都市です")
        engine.add("3", "奈良には歴史的な寺院があります")
        engine.commit()
        assert engine.count() == 3


# ---------------------------------------------------------------------------
# 4. search_semantic() が結果を返す
# ---------------------------------------------------------------------------

def test_search_semantic_returns_results():
    """search_semantic() が結果リストを返すこと。"""
    provider = FakeEmbedding()
    with SearchEngine("ja", embedding=provider) as engine:
        engine.add("1", "京都は日本の古都です")
        engine.commit()
        results = engine.search_semantic("日本の古い都")
        assert results
        assert results[0].id == "1"


def test_search_semantic_limit():
    """limit 指定が反映されること。"""
    provider = FakeEmbedding()
    with SearchEngine("ja", embedding=provider) as engine:
        engine.add("1", "a")
        engine.add("2", "b")
        engine.add("3", "c")
        engine.commit()
        results = engine.search_semantic("query", limit=2)
        assert len(results) <= 2


# ---------------------------------------------------------------------------
# 5. Keyword search と Semantic search が共存する
# ---------------------------------------------------------------------------

def test_keyword_and_semantic_coexist():
    """同一エンジンで search() と search_semantic() が両方動作すること。"""
    provider = FakeEmbedding()
    with SearchEngine("ja", embedding=provider) as engine:
        engine.add("1", "京都は日本の古都です")
        engine.add("2", "東京は日本最大の都市です")
        engine.commit()

        keyword_results = engine.search("京都")
        assert keyword_results

        semantic_results = engine.search_semantic("日本の古い都")
        assert semantic_results


# ---------------------------------------------------------------------------
# 6. embedding 無効時に search_semantic() は InvalidDocumentError
# ---------------------------------------------------------------------------

def test_search_semantic_raises_when_embedding_disabled():
    """embedding 未設定のエンジンで search_semantic() を呼ぶと InvalidDocumentError。"""
    with SearchEngine("ja") as engine:
        with pytest.raises(InvalidDocumentError, match="Semantic search is not enabled"):
            engine.search_semantic("日本の古い都")


# ---------------------------------------------------------------------------
# 7. FakeEmbedding + search_semantic() のエンドツーエンド
# ---------------------------------------------------------------------------

def test_custom_provider_search_semantic():
    """カスタム EmbeddingProvider 経由で search_semantic() が動作すること。"""
    provider = FakeEmbedding()
    with SearchEngine("ja", embedding=provider) as engine:
        engine.add("1", "test document")
        engine.commit()
        results = engine.search_semantic("query")
        assert results[0].id == "1"


# ---------------------------------------------------------------------------
# 8. search_semantic() に空クエリを渡すとエラー
# ---------------------------------------------------------------------------

def test_search_semantic_rejects_empty_query():
    """search_semantic() に空文字列を渡すと InvalidDocumentError になること。"""
    provider = FakeEmbedding()
    with SearchEngine("ja", embedding=provider) as engine:
        engine.add("1", "test")
        engine.commit()
        with pytest.raises(InvalidDocumentError):
            engine.search_semantic("")


# ---------------------------------------------------------------------------
# 9. filter_query との組み合わせ
# ---------------------------------------------------------------------------

def test_search_semantic_with_filter_query():
    """filter_query を指定したとき、一致しない文書が除外されること。"""
    provider = FakeEmbedding()
    with SearchEngine("ja", embedding=provider) as engine:
        engine.add("1", "京都", fields={"category_s": "city"})
        engine.add("2", "東京", fields={"category_s": "company"})
        engine.commit()

        results = engine.search_semantic(
            "都市", filter_query='category_s:"city"'
        )
        ids = [r.id for r in results]
        assert "1" in ids
        assert "2" not in ids
