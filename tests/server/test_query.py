"""tests/server/test_query.py

QueryPlanner のユニットテスト。
JVM 不要。
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from nlp4j_local_search.server.plan import (
    LexicalSearchPlan,
    VectorSearchPlan,
)
from nlp4j_local_search.server.query import (
    QueryError,
    QueryPlanner,
    UnsupportedQueryError,
    _quote,
    _match_value,
)


# ---------------------------------------------------------------------------
# field_type_resolver fixtures
# ---------------------------------------------------------------------------

def text_only_resolver(field: str) -> str:
    """全フィールドを TEXT として返す。"""
    return "TEXT"


def vector_resolver(field: str) -> str:
    """'vector' フィールドのみ VECTOR、それ以外は TEXT。"""
    if field == "vector":
        return "VECTOR"
    return "TEXT"


def keyword_resolver(field: str) -> str:
    """'maker_s' を KEYWORD、それ以外は TEXT。"""
    if field == "maker_s":
        return "KEYWORD"
    return "TEXT"


# ---------------------------------------------------------------------------
# ヘルパー関数テスト
# ---------------------------------------------------------------------------

class TestHelpers:

    def test_quote_simple(self):
        assert _quote("hello") == '"hello"'

    def test_quote_backslash(self):
        assert _quote("a\\b") == '"a\\\\b"'

    def test_quote_double_quote(self):
        assert _quote('say "hi"') == '"say \\"hi\\""'

    def test_match_value_simple(self):
        # スペースなし記号なしは引用符不要
        assert _match_value("京都") == "京都"

    def test_match_value_with_space(self):
        # スペースを含む場合は引用符付き
        result = _match_value("ヒューズ 交換")
        assert result.startswith('"')

    def test_match_value_with_colon(self):
        result = _match_value("a:b")
        assert result.startswith('"')


# ---------------------------------------------------------------------------
# QueryPlanner テスト
# ---------------------------------------------------------------------------

class TestQueryPlannerMatchAll:

    def setup_method(self):
        self.planner = QueryPlanner(text_only_resolver)

    def test_none_query(self):
        plan = self.planner.build(None, size=10)
        assert isinstance(plan, LexicalSearchPlan)
        assert plan.lucene_query == "*:*"

    def test_match_all(self):
        plan = self.planner.build({"match_all": {}}, size=10)
        assert isinstance(plan, LexicalSearchPlan)
        assert plan.lucene_query == "*:*"


class TestQueryPlannerQueryString:

    def setup_method(self):
        self.planner = QueryPlanner(text_only_resolver)

    def test_string_body(self):
        plan = self.planner.build({"query_string": "text_ja:京都"}, size=10)
        assert isinstance(plan, LexicalSearchPlan)
        assert plan.lucene_query == "text_ja:京都"

    def test_object_body(self):
        plan = self.planner.build(
            {"query_string": {"query": "text_ja:京都 AND category:city"}},
            size=10,
        )
        assert isinstance(plan, LexicalSearchPlan)
        assert "京都" in plan.lucene_query

    def test_missing_query_key(self):
        with pytest.raises(QueryError):
            self.planner.build({"query_string": {"bad_key": "value"}}, size=10)


class TestQueryPlannerTerm:

    def setup_method(self):
        self.planner = QueryPlanner(text_only_resolver)

    def test_simple(self):
        plan = self.planner.build({"term": {"maker_s": "NISSAN"}}, size=10)
        assert isinstance(plan, LexicalSearchPlan)
        assert 'maker_s:"NISSAN"' == plan.lucene_query

    def test_value_dict_form(self):
        plan = self.planner.build(
            {"term": {"maker_s": {"value": "TOYOTA"}}},
            size=10,
        )
        assert 'maker_s:"TOYOTA"' == plan.lucene_query

    def test_missing_value(self):
        with pytest.raises(QueryError):
            self.planner.build(
                {"term": {"maker_s": {"other": "x"}}},
                size=10,
            )

    def test_invalid_field_name(self):
        with pytest.raises(QueryError, match="Invalid field name"):
            self.planner.build({"term": {"bad field!": "value"}}, size=10)


class TestQueryPlannerRange:

    def setup_method(self):
        self.planner = QueryPlanner(text_only_resolver)

    def test_gte_lte(self):
        plan = self.planner.build(
            {"range": {"year": {"gte": 2020, "lte": 2025}}},
            size=10,
        )
        assert isinstance(plan, LexicalSearchPlan)
        assert "year:[2020 TO 2025]" == plan.lucene_query

    def test_gt_lt(self):
        plan = self.planner.build(
            {"range": {"year": {"gt": 2020, "lt": 2025}}},
            size=10,
        )
        assert "year:{2020 TO 2025}" == plan.lucene_query

    def test_open_upper(self):
        plan = self.planner.build(
            {"range": {"year": {"gte": 2020}}},
            size=10,
        )
        assert "year:[2020 TO *]" == plan.lucene_query

    def test_open_lower(self):
        plan = self.planner.build(
            {"range": {"year": {"lte": 2025}}},
            size=10,
        )
        assert "year:[* TO 2025]" == plan.lucene_query

    def test_gt_and_gte_error(self):
        with pytest.raises(QueryError):
            self.planner.build(
                {"range": {"year": {"gt": 2020, "gte": 2020}}},
                size=10,
            )

    def test_non_dict_condition_error(self):
        with pytest.raises(QueryError):
            self.planner.build({"range": {"year": "bad"}}, size=10)


class TestQueryPlannerMatchText:

    def setup_method(self):
        self.planner = QueryPlanner(text_only_resolver)

    def test_simple_string(self):
        plan = self.planner.build(
            {"match": {"text_ja": "ヒューズの交換"}},
            size=10,
        )
        assert isinstance(plan, LexicalSearchPlan)
        assert "text_ja:" in plan.lucene_query

    def test_object_form(self):
        plan = self.planner.build(
            {"match": {"text_ja": {"query": "ヒューズの交換"}}},
            size=10,
        )
        assert isinstance(plan, LexicalSearchPlan)
        assert "text_ja:" in plan.lucene_query

    def test_missing_query_in_object(self):
        with pytest.raises(QueryError):
            self.planner.build(
                {"match": {"text_ja": {"bad": "value"}}},
                size=10,
            )


class TestQueryPlannerMatchVector:

    def setup_method(self):
        self.planner = QueryPlanner(vector_resolver)

    def test_string_value(self):
        plan = self.planner.build(
            {"match": {"vector": "ヒューズの交換"}},
            size=10,
        )
        assert isinstance(plan, VectorSearchPlan)
        assert plan.field == "vector"
        assert plan.query_text == "ヒューズの交換"
        assert plan.k == 10  # size + offset (0)

    def test_object_value_with_k(self):
        plan = self.planner.build(
            {"match": {"vector": {"query": "ヒューズの交換", "k": 50, "num_candidates": 200}}},
            size=10,
        )
        assert isinstance(plan, VectorSearchPlan)
        assert plan.k == 50
        assert plan.num_candidates == 200

    def test_k_defaults_to_size_plus_offset(self):
        plan = self.planner.build(
            {"match": {"vector": "test"}},
            size=5,
            offset=3,
        )
        assert plan.k == 8  # 5 + 3

    def test_k_less_than_required_raises(self):
        with pytest.raises(QueryError, match="k must be"):
            self.planner.build(
                {"match": {"vector": {"query": "test", "k": 3}}},
                size=10,
                offset=0,
            )

    def test_invalid_value_type(self):
        with pytest.raises(QueryError):
            self.planner.build(
                {"match": {"vector": 12345}},
                size=10,
            )

    def test_missing_query_in_object(self):
        with pytest.raises(QueryError, match="VECTOR match requires"):
            self.planner.build(
                {"match": {"vector": {"num_candidates": 100}}},
                size=10,
            )


class TestQueryPlannerKnn:

    def setup_method(self):
        self.planner = QueryPlanner(vector_resolver)

    def test_query_text(self):
        plan = self.planner.build(
            {"knn": {"field": "vector", "query_text": "テスト", "k": 10}},
            size=10,
        )
        assert isinstance(plan, VectorSearchPlan)
        assert plan.query_text == "テスト"
        assert plan.query_vector is None

    def test_query_vector(self):
        plan = self.planner.build(
            {"knn": {"field": "vector", "query_vector": [0.1, 0.2], "k": 10}},
            size=10,
        )
        assert isinstance(plan, VectorSearchPlan)
        assert plan.query_vector == [0.1, 0.2]
        assert plan.query_text is None

    def test_both_raises(self):
        with pytest.raises(QueryError, match="exactly one"):
            self.planner.build(
                {"knn": {
                    "field": "vector",
                    "query_text": "test",
                    "query_vector": [0.1],
                    "k": 10,
                }},
                size=10,
            )

    def test_neither_raises(self):
        with pytest.raises(QueryError, match="exactly one"):
            self.planner.build(
                {"knn": {"field": "vector", "k": 10}},
                size=10,
            )

    def test_missing_field_raises(self):
        with pytest.raises(QueryError, match="knn.field is required"):
            self.planner.build(
                {"knn": {"query_text": "test", "k": 10}},
                size=10,
            )

    def test_with_filter(self):
        plan = self.planner.build(
            {
                "knn": {
                    "field": "vector",
                    "query_text": "テスト",
                    "k": 10,
                    "filter": {"term": {"maker_s": "NISSAN"}},
                }
            },
            size=10,
        )
        assert plan.filter_query is not None
        assert "NISSAN" in plan.filter_query

    def test_k_less_than_required_raises(self):
        with pytest.raises(QueryError, match="k must be"):
            self.planner.build(
                {"knn": {"field": "vector", "query_text": "test", "k": 3}},
                size=10,
                offset=0,
            )


class TestQueryPlannerBool:

    def setup_method(self):
        self.planner = QueryPlanner(vector_resolver)

    def test_must_lexical(self):
        plan = self.planner.build(
            {
                "bool": {
                    "must": [
                        {"term": {"maker_s": "NISSAN"}},
                        {"match": {"text_ja": "ヒューズ"}},
                    ]
                }
            },
            size=10,
        )
        assert isinstance(plan, LexicalSearchPlan)
        assert "NISSAN" in plan.lucene_query
        assert "ヒューズ" in plan.lucene_query

    def test_should_lexical(self):
        plan = self.planner.build(
            {
                "bool": {
                    "should": [
                        {"term": {"maker_s": "NISSAN"}},
                        {"term": {"maker_s": "TOYOTA"}},
                    ]
                }
            },
            size=10,
        )
        assert isinstance(plan, LexicalSearchPlan)
        assert " OR " in plan.lucene_query

    def test_must_not_lexical(self):
        plan = self.planner.build(
            {
                "bool": {
                    "must_not": [
                        {"term": {"maker_s": "NISSAN"}},
                    ]
                }
            },
            size=10,
        )
        assert isinstance(plan, LexicalSearchPlan)
        assert "NOT" in plan.lucene_query

    def test_empty_bool(self):
        plan = self.planner.build({"bool": {}}, size=10)
        assert isinstance(plan, LexicalSearchPlan)
        assert plan.lucene_query == "*:*"

    def test_vector_must_with_filter(self):
        plan = self.planner.build(
            {
                "bool": {
                    "must": [
                        {"match": {"vector": "ヒューズの交換"}}
                    ],
                    "filter": [
                        {"term": {"maker_s": "NISSAN"}}
                    ],
                }
            },
            size=10,
        )
        assert isinstance(plan, VectorSearchPlan)
        assert plan.filter_query is not None
        assert "NISSAN" in plan.filter_query

    def test_multiple_vector_in_must_raises(self):
        with pytest.raises(UnsupportedQueryError, match="Only one VECTOR"):
            self.planner.build(
                {
                    "bool": {
                        "must": [
                            {"match": {"vector": "test1"}},
                            {"match": {"vector": "test2"}},
                        ]
                    }
                },
                size=10,
            )

    def test_vector_with_should_raises(self):
        with pytest.raises(UnsupportedQueryError, match="bool.should"):
            self.planner.build(
                {
                    "bool": {
                        "must": [{"match": {"vector": "test"}}],
                        "should": [{"term": {"maker_s": "NISSAN"}}],
                    }
                },
                size=10,
            )

    def test_vector_with_lexical_must_raises(self):
        with pytest.raises(UnsupportedQueryError, match="Hybrid"):
            self.planner.build(
                {
                    "bool": {
                        "must": [
                            {"match": {"vector": "test"}},
                            {"term": {"maker_s": "NISSAN"}},
                        ]
                    }
                },
                size=10,
            )


class TestQueryPlannerErrors:

    def setup_method(self):
        self.planner = QueryPlanner(text_only_resolver)

    def test_unsupported_query_type(self):
        with pytest.raises(UnsupportedQueryError, match="Unsupported query type"):
            self.planner.build({"fuzzy": {"text_ja": "test"}}, size=10)

    def test_query_not_dict(self):
        with pytest.raises(QueryError, match="query must be an object"):
            self.planner.build("bad_string", size=10)  # type: ignore

    def test_multiple_top_level_keys(self):
        with pytest.raises(QueryError, match="exactly one query type"):
            self.planner.build({"term": {}, "match": {}}, size=10)

    def test_single_field_not_dict(self):
        with pytest.raises(QueryError, match="exactly one field"):
            self.planner.build({"term": "bad"}, size=10)

    def test_single_field_multiple_fields(self):
        with pytest.raises(QueryError, match="exactly one field"):
            self.planner.build({"term": {"a": "x", "b": "y"}}, size=10)
