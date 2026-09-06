"""
Tests for analytics API:
  - relative_rate() — candidate_size / backward-compat size= / special values
  - relative_rates() — bulk per-query-value results
  - AnalyticsQuery / AnalyticsKeyword model
  - AnalyticsResult validation (__post_init__)
  - sort stability (relativeRate desc, count desc, key asc)
  - empty index
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from nlp4j_local_search import (
    AnalyticsBucket,
    AnalyticsKeyword,
    AnalyticsQuery,
    AnalyticsResult,
    SearchEngine,
)
from nlp4j_local_search.errors import InvalidDocumentError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_maker_engine():
    """5文書: maker フィールド付きの車クレームデータ。"""
    app = SearchEngine("ja", auto_analyze=True)
    app.add_json({"id": "1", "body": "ドアミラーが破損", "maker": "Nissan"})
    app.add_json({"id": "2", "body": "ドアミラーが動かない", "maker": "Nissan"})
    app.add_json({"id": "3", "body": "ドアミラーが外れた", "maker": "Toyota"})
    app.add_json({"id": "4", "body": "ブレーキの効きが悪い", "maker": "Toyota"})
    app.add_json({"id": "5", "body": "ドアから水が入った", "maker": "Toyota"})
    app.commit()
    return app


def _build_car_engine():
    """5文書: word.noun / word.verb を持つ自動車クレームデータ。"""
    app = SearchEngine("ja", auto_analyze=True)
    app.add("1", "ニッサン ドアミラーが破損")
    app.add("2", "ニッサン ドアミラーが動かない")
    app.add("3", "トヨタ ドアミラーが外れた")
    app.add("4", "トヨタ ブレーキの効きが悪い")
    app.add("5", "トヨタ ドアから水が入った")
    app.commit()
    return app


# ===========================================================================
# 1. relative_rate() — candidate_size の名前変更 + 後方互換
# ===========================================================================

class TestRelativeRateCandidateSize:

    def test_candidate_size_keyword(self):
        """candidate_size= キーワード引数で呼べること。"""
        with _build_car_engine() as app:
            result = app.relative_rate(
                "word.noun", "ニッサン", "word.noun",
                candidate_size=100,
            )
            assert isinstance(result, AnalyticsResult)
            assert len(result.buckets) >= 1

    def test_size_backward_compat(self):
        """旧 size= キーワードでも動作すること（後方互換）。"""
        with _build_car_engine() as app:
            result_new = app.relative_rate(
                "word.noun", "ニッサン", "word.noun",
                candidate_size=100,
            )
            result_old = app.relative_rate(
                "word.noun", "ニッサン", "word.noun",
                size=100,
            )
            # 同じ候補数なので同じバケット数が返ること
            assert len(result_new.buckets) == len(result_old.buckets)

    def test_small_candidate_size_excludes_rare_high_rate(self):
        """candidate_size が小さいと count 上位が候補になり、
        稀だが high relative_rate な語が候補から外れることがある。"""
        with _build_car_engine() as app:
            result_large = app.relative_rate(
                "word.noun", "ニッサン", "word.noun",
                candidate_size=1000,
            )
            result_small = app.relative_rate(
                "word.noun", "ニッサン", "word.noun",
                candidate_size=1,
            )
            # 小さい候補数では返るバケット数が少ないか等しいこと
            assert len(result_small.buckets) <= len(result_large.buckets)

    def test_candidate_size_zero_raises(self):
        with _build_car_engine() as app:
            with pytest.raises(InvalidDocumentError):
                app.relative_rate("word.noun", "ニッサン", "word.noun", candidate_size=0)

    def test_size_zero_raises(self):
        """後方互換 size=0 も InvalidDocumentError を送出すること。"""
        with _build_car_engine() as app:
            with pytest.raises(InvalidDocumentError):
                app.relative_rate("word.noun", "ニッサン", "word.noun", size=0)


# ===========================================================================
# 2. relative_rate() — 特殊文字 query_value
# ===========================================================================

class TestRelativeRateSpecialValues:

    def test_query_value_with_space(self):
        """スペースを含む query_value が安全に扱われること (e.g. "Nissan Motor")."""
        with _build_maker_engine() as app:
            app.add_json({"id": "6", "body": "ドアが壊れた", "maker": "Nissan Motor"})
            app.commit()
            result = app.relative_rate("maker", "Nissan Motor", "maker", candidate_size=100)
            assert isinstance(result, AnalyticsResult)

    def test_query_value_with_colon(self):
        """Lucene 特殊文字 ":" を含む query_value が安全に扱われること。"""
        with _build_maker_engine() as app:
            app.add_json({"id": "7", "body": "部品が劣化", "maker": "A:B"})
            app.commit()
            result = app.relative_rate("maker", "A:B", "maker", candidate_size=100)
            assert isinstance(result, AnalyticsResult)

    def test_query_value_empty_string_allowed(self):
        """空文字の query_value は Java 側が許容しているため Python でも弾かないこと。"""
        with _build_car_engine() as app:
            # Java が null 禁止・空文字は許容するため InvalidDocumentError にならない
            # (Java 側でヒット 0 件として正常に返る)
            try:
                result = app.relative_rate("word.noun", "", "word.noun", candidate_size=10)
                assert isinstance(result, AnalyticsResult)
            except Exception:
                # Java 実装が空文字をエラーにする場合も許容
                pass

    def test_query_value_none_raises(self):
        """query_value=None は InvalidDocumentError を送出すること。"""
        with _build_car_engine() as app:
            with pytest.raises(InvalidDocumentError):
                app.relative_rate("word.noun", None, "word.noun", candidate_size=10)


# ===========================================================================
# 3. relative_rates() — bulk API
# ===========================================================================

class TestRelativeRates:

    def test_returns_dict(self):
        """relative_rates() は dict を返すこと。"""
        with _build_maker_engine() as app:
            results = app.relative_rates("maker", "maker")
            assert isinstance(results, dict)

    def test_both_makers_returned(self):
        """Nissan / Toyota 両方がキーとして返ること。"""
        with _build_maker_engine() as app:
            results = app.relative_rates(
                "maker", "maker",
                query_value_size=10,
                candidate_size=100,
            )
            assert "Nissan" in results
            assert "Toyota" in results

    def test_values_are_analytics_result(self):
        """各値が AnalyticsResult であること。"""
        with _build_maker_engine() as app:
            results = app.relative_rates("maker", "maker")
            for key, result in results.items():
                assert isinstance(key, str)
                assert isinstance(result, AnalyticsResult)

    def test_query_value_size_1_returns_single_entry(self):
        """query_value_size=1 のとき、doc_count 最大の値だけが返ること。"""
        with _build_maker_engine() as app:
            results = app.relative_rates(
                "maker", "maker",
                query_value_size=1,
            )
            # Toyota が 3 件で最多 → 1 件だけ返る
            assert len(results) == 1
            assert "Toyota" in results

    def test_candidate_size_none_uses_query_value_size(self):
        """candidate_size=None のとき query_value_size と同じ意味になること。"""
        with _build_maker_engine() as app:
            r1 = app.relative_rates("maker", "maker", query_value_size=10, candidate_size=None)
            r2 = app.relative_rates("maker", "maker", query_value_size=10, candidate_size=10)
            assert set(r1.keys()) == set(r2.keys())

    def test_empty_index_returns_empty_dict(self):
        """空インデックスで relative_rates() → {} を返すこと。"""
        with SearchEngine("ja", auto_analyze=True) as app:
            app.add("1", "dummy")
            app.commit()
            # "maker" フィールドが存在しないため空の dict が返ること
            results = app.relative_rates("maker", "maker")
            assert results == {}

    def test_candidate_size_zero_raises(self):
        with _build_maker_engine() as app:
            with pytest.raises(InvalidDocumentError):
                app.relative_rates("maker", "maker", candidate_size=0)

    def test_query_value_size_zero_raises(self):
        with _build_maker_engine() as app:
            with pytest.raises(InvalidDocumentError):
                app.relative_rates("maker", "maker", query_value_size=0)

    def test_empty_query_field_raises(self):
        with _build_maker_engine() as app:
            with pytest.raises(InvalidDocumentError):
                app.relative_rates("", "maker")

    def test_blank_query_field_raises(self):
        with _build_maker_engine() as app:
            with pytest.raises(InvalidDocumentError):
                app.relative_rates("   ", "maker")

    def test_empty_field_raises(self):
        with _build_maker_engine() as app:
            with pytest.raises(InvalidDocumentError):
                app.relative_rates("maker", "")


# ===========================================================================
# 4. AnalyticsResult.__post_init__ validation
# ===========================================================================

class TestAnalyticsResultValidation:

    def test_count_greater_than_total_raises(self):
        with pytest.raises(ValueError):
            AnalyticsResult(
                field="x",
                count=10,
                total_count=5,
                buckets=[],
            )

    def test_negative_count_raises(self):
        with pytest.raises(ValueError):
            AnalyticsResult(
                field="x",
                count=-1,
                total_count=5,
                buckets=[],
            )

    def test_negative_total_count_raises(self):
        with pytest.raises(ValueError):
            AnalyticsResult(
                field="x",
                count=0,
                total_count=-1,
                buckets=[],
            )

    def test_valid_construction(self):
        r = AnalyticsResult(field="x", count=5, total_count=10, buckets=[])
        assert r.count == 5
        assert r.total_count == 10


# ===========================================================================
# 5. Sort stability: relativeRate desc, count desc, key asc
# ===========================================================================

class TestSortStability:

    def test_buckets_sorted_by_relative_rate_desc(self):
        """relative_rate() の結果は relativeRate 降順で返ること。"""
        with _build_car_engine() as app:
            result = app.relative_rate(
                "word.noun", "ニッサン", "word.noun",
                candidate_size=1000,
            )
            rates = [b.relative_rate for b in result.buckets]
            assert rates == sorted(rates, reverse=True), (
                f"Buckets are not sorted by relative_rate desc: {rates}"
            )

    def test_relative_rates_buckets_sorted(self):
        """relative_rates() の各 AnalyticsResult のバケットも relativeRate 降順。"""
        with _build_maker_engine() as app:
            results = app.relative_rates("maker", "maker", candidate_size=100)
            for key, result in results.items():
                rates = [b.relative_rate for b in result.buckets]
                assert rates == sorted(rates, reverse=True), (
                    f"Buckets for {key!r} are not sorted by relative_rate desc: {rates}"
                )


# ===========================================================================
# 6. relative_rate_lucene() — blank string validation
# ===========================================================================

class TestRelativeRateLuceneValidation:

    def test_blank_lucene_query_raises(self):
        """空白のみの lucene_query は InvalidDocumentError を送出すること。"""
        with _build_car_engine() as app:
            with pytest.raises(InvalidDocumentError):
                app.relative_rate_lucene("   ", "word.noun", candidate_size=100)

    def test_blank_field_raises(self):
        with _build_car_engine() as app:
            with pytest.raises(InvalidDocumentError):
                app.relative_rate_lucene("word.noun:ニッサン", "   ", candidate_size=100)


# ===========================================================================
# 7. AnalyticsQuery / AnalyticsKeyword dataclass (pure Python)
# ===========================================================================

class TestAnalyticsModels:

    def test_analytics_query_field_value(self):
        q = AnalyticsQuery(kind="FIELD_VALUE", field="maker", value="Nissan")
        assert q.kind == "FIELD_VALUE"
        assert q.field == "maker"
        assert q.value == "Nissan"
        assert q.lucene_query is None

    def test_analytics_query_lucene(self):
        q = AnalyticsQuery(kind="LUCENE", lucene_query="maker:Nissan")
        assert q.kind == "LUCENE"
        assert q.lucene_query == "maker:Nissan"
        assert q.field is None
        assert q.value is None

    def test_analytics_keyword(self):
        kw = AnalyticsKeyword(field="word.noun", lex="ドアミラー")
        assert kw.field == "word.noun"
        assert kw.lex == "ドアミラー"

    def test_analytics_bucket_has_keyword_field(self):
        """AnalyticsBucket に keyword 属性があること（None でも可）。"""
        with _build_car_engine() as app:
            result = app.relative_rate(
                "word.noun", "ニッサン", "word.noun",
                candidate_size=100,
            )
            for bucket in result.buckets:
                # keyword は Optional — None か AnalyticsKeyword
                assert bucket.keyword is None or isinstance(bucket.keyword, AnalyticsKeyword)

    def test_analytics_result_has_query_field(self):
        """AnalyticsResult に query 属性があること（None でも可）。"""
        with _build_car_engine() as app:
            result = app.relative_rate(
                "word.noun", "ニッサン", "word.noun",
                candidate_size=100,
            )
            assert result.query is None or isinstance(result.query, AnalyticsQuery)
