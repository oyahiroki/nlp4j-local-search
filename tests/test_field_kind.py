"""
SearchEngine.field_kind() の統合テスト

Java の getFieldKind() を Python 公開 API として呼び出す確認テスト。
"""

import pytest

from nlp4j_local_search import SearchEngine
from nlp4j_local_search.errors import InvalidDocumentError, JavaSearchError


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def build_engine():
    """date / category_s / created_dt フィールドを持つエンジンを返す。"""
    engine = SearchEngine("en", auto_analyze=False)
    engine.add_json({
        "id": "1",
        "body": "test",
        "date": "2026-09-14",
        "category_s": "city",
        "created_dt": "2026-01-01",
    })
    engine.commit()
    return engine


# ---------------------------------------------------------------------------
# 1. DATE フィールドの kind
# ---------------------------------------------------------------------------

def test_field_kind_date():
    """date フィールドは \"DATE\" を返すこと。"""
    with build_engine() as engine:
        assert engine.field_kind("date") == "DATE"


def test_field_kind_dt_suffix():
    """_dt 接尾辞フィールドは \"DATE\" を返すこと。"""
    with build_engine() as engine:
        assert engine.field_kind("created_dt") == "DATE"


# ---------------------------------------------------------------------------
# 2. KEYWORD フィールドの kind
# ---------------------------------------------------------------------------

def test_field_kind_keyword():
    """_s 接尾辞フィールドは \"KEYWORD\" を返すこと。"""
    with build_engine() as engine:
        assert engine.field_kind("category_s") == "KEYWORD"


# ---------------------------------------------------------------------------
# 3. 存在しないフィールド
# ---------------------------------------------------------------------------

def test_field_kind_unknown():
    """存在しないフィールドは None を返すこと。"""
    with build_engine() as engine:
        assert engine.field_kind("unknown_field") is None


# ---------------------------------------------------------------------------
# 4. 入力バリデーション
# ---------------------------------------------------------------------------

def test_field_kind_empty_string():
    """空文字列は InvalidDocumentError を送出すること。"""
    with build_engine() as engine:
        with pytest.raises(InvalidDocumentError):
            engine.field_kind("")


def test_field_kind_whitespace_only():
    """空白のみは InvalidDocumentError を送出すること。"""
    with build_engine() as engine:
        with pytest.raises(InvalidDocumentError):
            engine.field_kind("   ")


# ---------------------------------------------------------------------------
# 5. view() との連携 — date フィールドは year がデフォルトになること
# ---------------------------------------------------------------------------

def test_view_date_field_default_interval_year():
    """view('date') は field_kind() が DATE を返すため interval=year になること。"""
    with build_engine() as engine:
        result = engine.view("date")
        assert result.fields[0].interval == "year"


# ---------------------------------------------------------------------------
# 6. date_histogram() の interval 検証
# ---------------------------------------------------------------------------

def test_date_histogram_day_raises():
    """interval='day' は Python 側で InvalidDocumentError になること。"""
    with build_engine() as engine:
        with pytest.raises(InvalidDocumentError):
            engine.date_histogram("created_dt", "day")


def test_date_histogram_valid_intervals():
    """year / month / hour の各 interval は正常に動作すること。"""
    with build_engine() as engine:
        assert isinstance(engine.date_histogram("created_dt", "year"), list)
        assert isinstance(engine.date_histogram("created_dt", "month"), list)
