"""tests/server/test_models.py

Pydantic モデルのシリアライズ / バリデーションテスト。
JVM 不要。
"""
import pytest
from pydantic import ValidationError

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from nlp4j_local_search.server.models import (
    CountRequest,
    SearchRequest,
    SourceFilter,
)


class TestSearchRequest:

    def test_defaults(self):
        req = SearchRequest()
        assert req.query is None
        assert req.size == 10
        assert req.from_ == 0
        assert req.source is None
        assert req.aggs is None

    def test_from_alias(self):
        """JSON の "from" フィールドが from_ にマッピングされる。"""
        req = SearchRequest.model_validate({"from": 5, "size": 20})
        assert req.from_ == 5
        assert req.size == 20

    def test_source_bool(self):
        req = SearchRequest.model_validate({"_source": False})
        assert req.source is False

    def test_source_list(self):
        req = SearchRequest.model_validate({"_source": ["title", "body"]})
        assert req.source == ["title", "body"]

    def test_source_filter_object(self):
        req = SearchRequest.model_validate({
            "_source": {"includes": ["title"], "excludes": ["body"]}
        })
        assert isinstance(req.source, SourceFilter)
        assert req.source.includes == ["title"]
        assert req.source.excludes == ["body"]

    def test_size_zero_allowed(self):
        req = SearchRequest.model_validate({"size": 0})
        assert req.size == 0

    def test_size_negative_rejected(self):
        with pytest.raises(ValidationError):
            SearchRequest.model_validate({"size": -1})

    def test_from_negative_rejected(self):
        with pytest.raises(ValidationError):
            SearchRequest.model_validate({"from": -1})

    def test_extra_fields_allowed(self):
        """extra='allow' なので未知フィールドを受け入れる。"""
        req = SearchRequest.model_validate({"unknown_field": "value"})
        assert req.query is None  # エラーにならない

    def test_query_dict(self):
        req = SearchRequest.model_validate({
            "query": {"match": {"text_ja": "京都"}},
            "size": 5,
        })
        assert req.query == {"match": {"text_ja": "京都"}}
        assert req.size == 5


class TestCountRequest:

    def test_defaults(self):
        req = CountRequest()
        assert req.query is None

    def test_with_query(self):
        req = CountRequest.model_validate({
            "query": {"term": {"maker_s": "NISSAN"}}
        })
        assert req.query == {"term": {"maker_s": "NISSAN"}}


class TestSourceFilter:

    def test_all_none(self):
        sf = SourceFilter()
        assert sf.includes is None
        assert sf.excludes is None

    def test_includes_only(self):
        sf = SourceFilter(includes=["a", "b"])
        assert sf.includes == ["a", "b"]
        assert sf.excludes is None
