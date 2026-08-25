"""
Tests for SearchEngine.relative_rate() — relativeRate analytics.

Mirrors Java Example10_TextMining_Ja3.java.
Requires a JVM with nlp4j-localsearch.jar 0.5.1.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from nlp4j_local_search import AnalyticsBucket, AnalyticsResult, SearchEngine
from nlp4j_local_search.errors import InvalidDocumentError


# ---------------------------------------------------------------------------
# Helper: build the standard 5-document dataset used in Example10
# ---------------------------------------------------------------------------

def _build_car_engine():
    """Return an open SearchEngine pre-loaded with 5 car complaint documents."""
    app = SearchEngine("ja", auto_analyze=True)
    app.add("1", "ニッサン ドアミラーが破損")
    app.add("2", "ニッサン ドアミラーが動かない")
    app.add("3", "トヨタ ドアミラーが外れた")
    app.add("4", "トヨタ ブレーキの効きが悪い")
    app.add("5", "トヨタ ドアから水が入った")
    app.commit()
    return app


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

def test_relative_rate_returns_analytics_result():
    """relative_rate() は AnalyticsResult を返すこと。"""
    with _build_car_engine() as app:
        result = app.relative_rate(
            query_field="word.noun",
            query_value="ニッサン",
            field="word.noun",
            size=100,
        )
        assert isinstance(result, AnalyticsResult)


def test_relative_rate_result_fields():
    """AnalyticsResult の属性が正しく設定されること。"""
    with _build_car_engine() as app:
        result = app.relative_rate(
            query_field="word.noun",
            query_value="ニッサン",
            field="word.noun",
            size=100,
        )
        assert result.query_field == "word.noun"
        assert result.query_value == "ニッサン"
        assert result.field == "word.noun"
        assert isinstance(result.count, int)
        assert isinstance(result.total_count, int)
        assert result.count >= 1
        assert result.total_count >= result.count


# ---------------------------------------------------------------------------
# Bucket structure
# ---------------------------------------------------------------------------

def test_relative_rate_buckets_are_analytics_bucket():
    """buckets の各要素が AnalyticsBucket インスタンスであること。"""
    with _build_car_engine() as app:
        result = app.relative_rate(
            query_field="word.noun",
            query_value="ニッサン",
            field="word.noun",
            size=100,
        )
        for bucket in result.buckets:
            assert isinstance(bucket, AnalyticsBucket)


def test_relative_rate_bucket_fields():
    """AnalyticsBucket の各属性型が正しいこと。"""
    with _build_car_engine() as app:
        result = app.relative_rate(
            query_field="word.noun",
            query_value="ニッサン",
            field="word.noun",
            size=100,
        )
        for bucket in result.buckets:
            assert isinstance(bucket.field, str)
            assert isinstance(bucket.key, str)
            assert isinstance(bucket.count, int)
            assert isinstance(bucket.all_count, int)
            assert isinstance(bucket.relative_rate, float)


# ---------------------------------------------------------------------------
# Semantic correctness (mirrors Example10 expected output)
# ---------------------------------------------------------------------------

def test_relative_rate_nissan_nouns_contain_nissan():
    """ニッサン文書の word.noun を relative_rate() すると 'ニッサン' が bucket に現れること。"""
    with _build_car_engine() as app:
        result = app.relative_rate(
            query_field="word.noun",
            query_value="ニッサン",
            field="word.noun",
            size=100,
        )
        keys = {b.key for b in result.buckets}
        assert "ニッサン" in keys, f"Expected 'ニッサン' in buckets, got: {keys}"


def test_relative_rate_positive_relative_rate():
    """各 bucket の relative_rate が正であること。"""
    with _build_car_engine() as app:
        result = app.relative_rate(
            query_field="word.noun",
            query_value="ニッサン",
            field="word.noun",
            size=100,
        )
        for bucket in result.buckets:
            assert bucket.relative_rate > 0, (
                f"relative_rate must be positive, got {bucket.relative_rate} for '{bucket.key}'"
            )


def test_relative_rate_size_limits_buckets():
    """size パラメータでバケット数が制限されること。"""
    with _build_car_engine() as app:
        result_large = app.relative_rate(
            query_field="word.noun",
            query_value="ニッサン",
            field="word.noun",
            size=100,
        )
        result_small = app.relative_rate(
            query_field="word.noun",
            query_value="ニッサン",
            field="word.noun",
            size=1,
        )
        assert len(result_small.buckets) <= 1
        assert len(result_large.buckets) >= len(result_small.buckets)


def test_relative_rate_verb_field():
    """word.verb フィールドを指定した relative_rate() が動作すること。"""
    with _build_car_engine() as app:
        result = app.relative_rate(
            query_field="word.noun",
            query_value="ニッサン",
            field="word.verb",
            size=100,
        )
        assert isinstance(result, AnalyticsResult)
        keys = {b.key for b in result.buckets}
        assert "動く" in keys, f"Expected '動く' in word.verb buckets for ニッサン, got: {keys}"


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_relative_rate_empty_query_field_raises():
    with _build_car_engine() as app:
        with pytest.raises(InvalidDocumentError):
            app.relative_rate(
                query_field="",
                query_value="ニッサン",
                field="word.noun",
            )


def test_relative_rate_empty_field_raises():
    with _build_car_engine() as app:
        with pytest.raises(InvalidDocumentError):
            app.relative_rate(
                query_field="word.noun",
                query_value="ニッサン",
                field="",
            )


def test_relative_rate_zero_size_raises():
    with _build_car_engine() as app:
        with pytest.raises(InvalidDocumentError):
            app.relative_rate(
                query_field="word.noun",
                query_value="ニッサン",
                field="word.noun",
                size=0,
            )


def test_relative_rate_none_query_value_raises():
    with _build_car_engine() as app:
        with pytest.raises(InvalidDocumentError):
            app.relative_rate(
                query_field="word.noun",
                query_value=None,
                field="word.noun",
            )
