"""tests/server/test_plan.py

SearchPlan データクラスのテスト。
JVM 不要。
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from nlp4j_local_search.server.plan import (
    LexicalSearchPlan,
    SearchPlan,
    VectorSearchPlan,
)


class TestLexicalSearchPlan:

    def test_is_search_plan(self):
        plan = LexicalSearchPlan("text_ja:京都")
        assert isinstance(plan, SearchPlan)

    def test_lucene_query(self):
        plan = LexicalSearchPlan("*:*")
        assert plan.lucene_query == "*:*"

    def test_equality(self):
        assert LexicalSearchPlan("a:b") == LexicalSearchPlan("a:b")
        assert LexicalSearchPlan("a:b") != LexicalSearchPlan("a:c")


class TestVectorSearchPlan:

    def test_is_search_plan(self):
        plan = VectorSearchPlan(field="vector")
        assert isinstance(plan, SearchPlan)

    def test_defaults(self):
        plan = VectorSearchPlan(field="vector")
        assert plan.field == "vector"
        assert plan.query_text is None
        assert plan.query_vector is None
        assert plan.model_id is None
        assert plan.k == 10
        assert plan.num_candidates is None
        assert plan.filter_query is None

    def test_with_query_text(self):
        plan = VectorSearchPlan(
            field="vector",
            query_text="ヒューズの交換",
            k=20,
            num_candidates=100,
        )
        assert plan.query_text == "ヒューズの交換"
        assert plan.k == 20
        assert plan.num_candidates == 100

    def test_with_query_vector(self):
        plan = VectorSearchPlan(
            field="vector",
            query_vector=[0.1, 0.2, 0.3],
            k=5,
        )
        assert plan.query_vector == [0.1, 0.2, 0.3]

    def test_filter_query_mutable(self):
        """filter_query はフィールドを後から代入できる。"""
        plan = VectorSearchPlan(field="vector", query_text="test", k=10)
        plan.filter_query = 'maker_s:"NISSAN"'
        assert plan.filter_query == 'maker_s:"NISSAN"'
