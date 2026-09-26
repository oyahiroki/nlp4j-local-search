"""
Tests for SearchEngine.delete() — requires Java 21+.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from nlp4j_local_search import SearchEngine
from nlp4j_local_search.errors import InvalidDocumentError


def test_delete_basic():
    """delete() で登録済みドキュメントを削除できること。"""
    with SearchEngine("ja") as engine:
        engine.add("1", "東京")
        engine.add("2", "京都")
        engine.add("3", "大阪")
        engine.commit()
        assert engine.count() == 3

        engine.delete("2")
        engine.commit()

        assert engine.count() == 2


def test_delete_reduces_search_results():
    """delete() 後に commit() すると検索結果から除外されること。"""
    with SearchEngine("ja") as engine:
        engine.add("1", "東京都は日本の都道府県")
        engine.add("2", "京都は日本の都市")
        engine.add("3", "京都市には任天堂の本社がある")
        engine.commit()

        results_before = engine.search("京都")
        assert len(results_before) == 2

        engine.delete("2")
        engine.commit()

        results_after = engine.search("京都")
        assert len(results_after) == 1
        assert results_after[0].id == "3"


def test_delete_nonexistent_id_is_noop():
    """存在しない ID を delete() しても例外が発生しないこと。"""
    with SearchEngine("ja") as engine:
        engine.add("1", "東京")
        engine.commit()

        # 存在しない ID → エラーなし
        engine.delete("nonexistent")
        engine.commit()

        assert engine.count() == 1


def test_delete_empty_id_raises():
    """空文字列を delete() すると InvalidDocumentError になること。"""
    with SearchEngine("ja") as engine:
        engine.add("1", "東京")
        engine.commit()

        with pytest.raises(InvalidDocumentError):
            engine.delete("")


def test_delete_all_documents():
    """全ドキュメントを delete() して commit() すると count() が 0 になること。"""
    with SearchEngine("ja") as engine:
        engine.add("1", "東京")
        engine.add("2", "京都")
        engine.commit()

        engine.delete("1")
        engine.delete("2")
        engine.commit()

        assert engine.count() == 0


def test_delete_then_readd():
    """delete() 後に同じ ID で再登録できること。"""
    with SearchEngine("ja") as engine:
        engine.add("1", "東京")
        engine.commit()
        assert engine.count() == 1

        engine.delete("1")
        engine.commit()
        assert engine.count() == 0

        engine.add("1", "東京（再登録）")
        engine.commit()
        assert engine.count() == 1
