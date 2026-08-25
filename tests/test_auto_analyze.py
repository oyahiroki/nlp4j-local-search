"""
Tests for auto_analyze option in SearchEngine.

Mirrors Java Example11_AutoAnalyzeOption.java.
Requires a JVM with nlp4j-localsearch.jar 0.5.0.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from nlp4j_local_search import SearchEngine


def test_auto_analyze_true_verb():
    """auto_analyze=True で日本語テキストを追加すると word.verb に "行く" が集計される。"""
    with SearchEngine("ja", auto_analyze=True) as app:
        app.add("1", "私は歩いて学校に行きました。")
        app.commit()

        result = app.aggregate("word.verb", size=10)
        buckets = result["aggregations"]["word.verb"]["buckets"]
        keys = {bucket["key"] for bucket in buckets}

        assert "行く" in keys, f"Expected '行く' in word.verb buckets, got: {keys}"


def test_auto_analyze_false_verb():
    """auto_analyze=False では word.verb に "行く" が集計されない。"""
    with SearchEngine("ja", auto_analyze=False) as app:
        app.add("1", "私は歩いて学校に行きました。")
        app.commit()

        result = app.aggregate("word.verb", size=10)
        buckets = result["aggregations"]["word.verb"]["buckets"]
        keys = {bucket["key"] for bucket in buckets}

        assert "行く" not in keys, f"Expected '行く' NOT in word.verb buckets, got: {keys}"


def test_auto_analyze_true_noun():
    """auto_analyze=True で名詞 word.noun が抽出される。"""
    with SearchEngine("ja", auto_analyze=True) as app:
        app.add("1", "東京は日本の首都です。")
        app.commit()

        result = app.aggregate("word.noun", size=20)
        buckets = result["aggregations"]["word.noun"]["buckets"]
        keys = {bucket["key"] for bucket in buckets}

        # 「東京」か「日本」か「首都」のいずれかが名詞として抽出されること
        assert keys, "Expected at least one noun to be extracted"
        assert any(k in keys for k in ("東京", "日本", "首都")), (
            f"Expected at least one of 東京/日本/首都 in word.noun, got: {keys}"
        )


def test_auto_analyze_default_is_true():
    """auto_analyze のデフォルトは True で、形態素解析が有効になっている。"""
    with SearchEngine("ja") as app:
        app.add("1", "私は歩いて学校に行きました。")
        app.commit()

        result = app.aggregate("word.verb", size=10)
        buckets = result["aggregations"]["word.verb"]["buckets"]
        keys = {bucket["key"] for bucket in buckets}

        assert "行く" in keys, f"Default auto_analyze should be True; expected '行く' in {keys}"


def test_auto_analyze_attribute_stored():
    """SearchEngine.auto_analyze 属性が正しく格納される。"""
    with SearchEngine("ja", auto_analyze=True) as app:
        assert app.auto_analyze is True

    with SearchEngine("ja", auto_analyze=False) as app:
        assert app.auto_analyze is False


def test_auto_analyze_multiple_documents():
    """複数文書を追加した場合も形態素解析が正しく機能する。"""
    with SearchEngine("ja", auto_analyze=True) as app:
        app.add("1", "ニッサン ドアミラーが破損")
        app.add("2", "ニッサン ドアミラーが動かない")
        app.add("3", "トヨタ ドアミラーが外れた")
        app.add("4", "トヨタ ブレーキの効きが悪い")
        app.add("5", "トヨタ ドアから水が入った")
        app.commit()

        result = app.aggregate("word.noun", size=100)
        buckets = result["aggregations"]["word.noun"]["buckets"]
        keys = {bucket["key"] for bucket in buckets}

        # ニッサン・トヨタ・ドアミラーなどが名詞として抽出されること
        assert "ニッサン" in keys, f"Expected 'ニッサン' in word.noun, got: {keys}"
        assert "トヨタ" in keys, f"Expected 'トヨタ' in word.noun, got: {keys}"
