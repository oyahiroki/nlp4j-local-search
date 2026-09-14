"""
DATE histogram 統合テスト

Java の DateHistogramBucket / DateHistogramInterval を Python から
JPype 経由で呼び出す統合確認テスト。
"""

import pytest

from nlp4j_local_search import DateHistogramBucket, SearchEngine
from nlp4j_local_search.errors import InvalidDocumentError, JavaSearchError


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def build_engine():
    """3件の文書（Nissan×2、Toyota×1）を持つエンジンを返す。"""
    engine = SearchEngine("en", auto_analyze=False)
    engine.add_json({"id": "1", "body": "Nissan", "created_dt": "2023-06-01"})
    engine.add_json({"id": "2", "body": "Nissan", "created_dt": "2026-03-15"})
    engine.add_json({"id": "3", "body": "Toyota", "created_dt": "2020-01-01"})
    engine.commit()
    return engine


# ---------------------------------------------------------------------------
# 1. DATE 派生フィールドの統合確認（新 JAR 読み込み確認を兼ねる）
# ---------------------------------------------------------------------------

def test_date_derived_fields_searchable():
    """_dt 登録で year/month/day/hour 派生フィールドが検索可能になること。"""
    with SearchEngine("ja", auto_analyze=False, time_zone="Asia/Tokyo") as engine:
        engine.add_json({
            "id": "1",
            "body": "イベントA",
            "event_dt": "2026-08-19T20:00:00+09:00",
        })
        engine.commit()

        assert len(engine.search("event_year_i:2026")) == 1
        assert len(engine.search("event_month_i:8")) == 1
        assert len(engine.search("event_day_i:19")) == 1
        assert len(engine.search("event_hour_i:20")) == 1


def test_date_only_no_hour_field():
    """date-only 文書では hour_i が生成されないこと。"""
    with SearchEngine("en", auto_analyze=False) as engine:
        engine.add_json({
            "id": "1",
            "body": "A",
            "event_dt": "2026-08-19",
        })
        engine.commit()

        assert len(engine.search("event_year_i:2026")) == 1
        # date-only なので hour_i は存在しない → 0件
        assert len(engine.search("event_hour_i:0")) == 0


# ---------------------------------------------------------------------------
# 2. YEAR histogram 基本
# ---------------------------------------------------------------------------

def test_date_histogram_year_basic():
    """全文書の YEAR histogram が 0件補完付きで返ること。"""
    with build_engine() as engine:
        buckets = engine.date_histogram("created_dt", "year")

        assert [b.key for b in buckets] == [
            "2020", "2021", "2022", "2023", "2024", "2025", "2026",
        ]
        counts = {b.key: b.doc_count for b in buckets}
        assert counts["2020"] == 1
        assert counts["2021"] == 0
        assert counts["2022"] == 0
        assert counts["2023"] == 1
        assert counts["2024"] == 0
        assert counts["2025"] == 0
        assert counts["2026"] == 1


def test_date_histogram_returns_list_of_dataclass():
    """戻り値が DateHistogramBucket のリストであること。"""
    with build_engine() as engine:
        buckets = engine.date_histogram("created_dt", "year")
        assert isinstance(buckets, list)
        assert all(isinstance(b, DateHistogramBucket) for b in buckets)


# ---------------------------------------------------------------------------
# 3. query 付き YEAR histogram
# ---------------------------------------------------------------------------

def test_date_histogram_query_min_max():
    """query 指定時に min/max が query 対象文書に限定されること。"""
    with build_engine() as engine:
        buckets = engine.date_histogram("created_dt", "year", query="Nissan")

        # Toyota(2020) は範囲を広げない
        assert [b.key for b in buckets] == [
            "2023", "2024", "2025", "2026",
        ]
        assert [b.doc_count for b in buckets] == [1, 0, 0, 1]


def test_date_histogram_no_match():
    """マッチなしの場合は空リストを返すこと。"""
    with build_engine() as engine:
        buckets = engine.date_histogram(
            "created_dt", "year", query="NonExistingBrand"
        )
        assert buckets == []


# ---------------------------------------------------------------------------
# 4. MONTH histogram
# ---------------------------------------------------------------------------

def test_date_histogram_month_zero_gap():
    """MONTH histogram が 0件補完付きで返ること。"""
    with SearchEngine("en", auto_analyze=False) as engine:
        engine.add_json({"id": "1", "body": "A", "created_dt": "2026-01-01"})
        engine.add_json({"id": "2", "body": "B", "created_dt": "2026-03-01"})
        engine.commit()

        buckets = engine.date_histogram("created_dt", "month")

        assert [b.key for b in buckets] == [
            "2026-01", "2026-02", "2026-03",
        ]
        assert [b.doc_count for b in buckets] == [1, 0, 1]


# ---------------------------------------------------------------------------
# 5. HOUR histogram
# ---------------------------------------------------------------------------

def test_date_histogram_hour_zero_gap():
    """HOUR histogram が 0件補完付きで返ること。"""
    with SearchEngine("en", auto_analyze=False) as engine:
        engine.add_json({
            "id": "1", "body": "A",
            "created_dt": "2026-01-01T08:00:00",
        })
        engine.add_json({
            "id": "2", "body": "B",
            "created_dt": "2026-01-01T10:00:00",
        })
        engine.commit()

        buckets = engine.date_histogram("created_dt", "hour")

        assert [b.key for b in buckets] == [
            "2026-01-01T08",
            "2026-01-01T09",
            "2026-01-01T10",
        ]
        assert [b.doc_count for b in buckets] == [1, 0, 1]


# ---------------------------------------------------------------------------
# 6. filters 付き histogram
# ---------------------------------------------------------------------------

def test_date_histogram_filter_min_max():
    """filters 指定時に min/max が filter 対象文書に限定されること。"""
    with SearchEngine("en", auto_analyze=False) as engine:
        engine.add_json({
            "id": "1", "body": "car", "brand_s": "Nissan",
            "created_dt": "2023-05-01",
        })
        engine.add_json({
            "id": "2", "body": "car", "brand_s": "Nissan",
            "created_dt": "2026-07-01",
        })
        engine.add_json({
            "id": "3", "body": "car", "brand_s": "Toyota",
            "created_dt": "2020-01-01",
        })
        engine.commit()

        buckets = engine.date_histogram(
            "created_dt", "year",
            filters={"brand_s": "Nissan"},
        )

        assert buckets[0].key == "2023"
        assert buckets[-1].key == "2026"
        assert not any(b.key == "2020" for b in buckets)


def test_date_histogram_query_and_filter():
    """query + filters の両方を適用した histogram が正しいこと。"""
    with SearchEngine("en", auto_analyze=False) as engine:
        engine.add_json({
            "id": "1", "body": "sport car", "brand_s": "Nissan",
            "created_dt": "2023-01-01",
        })
        engine.add_json({
            "id": "2", "body": "sport car", "brand_s": "Toyota",
            "created_dt": "2024-01-01",
        })
        engine.add_json({
            "id": "3", "body": "truck", "brand_s": "Nissan",
            "created_dt": "2025-01-01",
        })
        engine.commit()

        buckets = engine.date_histogram(
            "created_dt", "year",
            query="sport",
            filters={"brand_s": "Nissan"},
        )

        assert len(buckets) == 1
        assert buckets[0].key == "2023"
        assert buckets[0].doc_count == 1


# ---------------------------------------------------------------------------
# 7. エラー条件
# ---------------------------------------------------------------------------

def test_date_histogram_invalid_interval():
    """不正な interval では InvalidDocumentError を送出すること。"""
    with build_engine() as engine:
        with pytest.raises(InvalidDocumentError):
            engine.date_histogram("created_dt", "invalid")


def test_date_histogram_empty_field():
    """空の field では InvalidDocumentError を送出すること。"""
    with build_engine() as engine:
        with pytest.raises(InvalidDocumentError):
            engine.date_histogram("", "year")


def test_date_histogram_empty_interval():
    """空の interval では InvalidDocumentError を送出すること。"""
    with build_engine() as engine:
        with pytest.raises(InvalidDocumentError):
            engine.date_histogram("created_dt", "")


def test_date_histogram_non_date_field():
    """DATE でないフィールドへの histogram は JavaSearchError になること。"""
    with SearchEngine("en", auto_analyze=False) as engine:
        engine.add_json({"id": "1", "body": "hello", "category": "A"})
        engine.commit()

        with pytest.raises(JavaSearchError):
            engine.date_histogram("category", "year")


# ---------------------------------------------------------------------------
# 8. view(interval=...) テスト
# ---------------------------------------------------------------------------

def test_view_date_histogram_year():
    """view(interval='year') が時系列順の ViewResult を返すこと。"""
    with SearchEngine("en", auto_analyze=False) as engine:
        engine.add_json({"id": "1", "body": "Nissan", "created_dt": "2023-01-01"})
        engine.add_json({"id": "2", "body": "Nissan", "created_dt": "2026-01-01"})
        engine.commit()

        result = engine.view("created_dt", interval="year")

        field = result.fields[0]
        assert field.field == "created_dt"
        assert field.interval == "year"

        assert [b.key for b in field.buckets] == [
            "2023", "2024", "2025", "2026",
        ]
        assert [b.count for b in field.buckets] == [1, 0, 0, 1]
        assert result.sort_key == "key"


def test_view_date_histogram_with_query():
    """view(field, query, interval=...) が query 付き histogram を返すこと。"""
    with build_engine() as engine:
        result = engine.view("created_dt", "Nissan", interval="year")

        buckets = result.fields[0].buckets
        assert [b.key for b in buckets] == [
            "2023", "2024", "2025", "2026",
        ]


def test_view_date_histogram_str_output():
    """str(result) が時系列フォーマットで出力されること。"""
    with SearchEngine("en", auto_analyze=False) as engine:
        engine.add_json({"id": "1", "body": "A", "created_dt": "2025-01-01"})
        engine.commit()

        result = engine.view("created_dt", interval="year")
        text = str(result)

        assert "Interval: year" in text
        assert "Values are ordered chronologically." in text
        assert "Period" in text


def test_view_interval_requires_field():
    """interval 指定時に field なしは InvalidDocumentError になること。"""
    with SearchEngine("en", auto_analyze=False) as engine:
        with pytest.raises(InvalidDocumentError):
            engine.view(interval="year")


def test_view_date_histogram_size_not_supported():
    """interval + size の組み合わせは InvalidDocumentError になること。"""
    with SearchEngine("en", auto_analyze=False) as engine:
        with pytest.raises(InvalidDocumentError):
            engine.view("created_dt", interval="year", size=3)


# ---------------------------------------------------------------------------
# 9. 通常 view() / relativeRate の回帰テスト
# ---------------------------------------------------------------------------

def test_regular_view_still_works():
    """従来の view() が引き続き動作すること。"""
    with SearchEngine("en", auto_analyze=False) as engine:
        engine.add_json({"id": "1", "body": "Kyoto city Japan", "category": "city"})
        engine.add_json({"id": "2", "body": "Tokyo city Japan", "category": "city"})
        engine.add_json({"id": "3", "body": "Nintendo company Kyoto", "category": "company"})
        engine.commit()

        result = engine.view("category")
        assert result.sort_key == "count"
        assert result.fields[0].interval is None
        assert len(result.fields[0].buckets) > 0
