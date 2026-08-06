"""
新機能テスト:
  - MultiValued フィールドの登録・フィルター検索  (Example07 相当)
  - Aggregation API  (Example06 相当)
  - search_json() による OpenSearch Query DSL 検索
  - search_response_json() による AND 条件検索
  - バリデーション
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nlp4j_local_search import SearchEngine
from nlp4j_local_search.errors import InvalidDocumentError


# ---------------------------------------------------------------------------
# テスト用ドキュメント (Example06 / Example07 共通)
# ---------------------------------------------------------------------------
_DOCS = [
    {"id": "1", "body": "Kyoto is a historic city.",                    "tags": ["city", "tourism", "Japan"]},
    {"id": "2", "body": "Nintendo is headquartered in Kyoto.",          "tags": ["company", "Japan"]},
    {"id": "3", "body": "Tokyo is the capital city of Japan.",          "tags": ["city", "capital", "Japan"]},
    {"id": "4", "body": "Paris is a beautiful city in France.",         "tags": ["city", "tourism", "France"]},
    {"id": "5", "body": "Sony is a Japanese company based in Tokyo.",   "tags": ["company", "Japan"]},
]


def _make_engine():
    engine = SearchEngine("en")
    for doc in _DOCS:
        engine.add_json(doc)
    engine.commit()
    return engine


# ---------------------------------------------------------------------------
# MultiValued フィールド: 単一値フィルター検索
# ---------------------------------------------------------------------------
def test_multivalued_filter_single():
    print("=== MultiValued: 単一値フィルター検索 ===")
    with _make_engine() as engine:
        # tags="Japan" → id=1,2,3,5 (4件)
        results = engine.search("", limit=10, filters={"tags": "Japan"})
        ids = {r.id for r in results}
        print(f"  tags=Japan: {sorted(ids)}")
        assert ids == {"1", "2", "3", "5"}, f"Unexpected: {ids}"

        # tags="city" → id=1,3,4 (3件)
        results = engine.search("", limit=10, filters={"tags": "city"})
        ids = {r.id for r in results}
        print(f"  tags=city: {sorted(ids)}")
        assert ids == {"1", "3", "4"}, f"Unexpected: {ids}"

        # tags="tourism" → id=1,4 (2件)
        results = engine.search("", limit=10, filters={"tags": "tourism"})
        ids = {r.id for r in results}
        print(f"  tags=tourism: {sorted(ids)}")
        assert ids == {"1", "4"}, f"Unexpected: {ids}"

        # tags="sports" → 0件
        results = engine.search("", limit=10, filters={"tags": "sports"})
        ids = [r.id for r in results]
        print(f"  tags=sports (0件): {ids}")
        assert ids == [], f"Unexpected: {ids}"

    print("✓ OK\n")


# ---------------------------------------------------------------------------
# MultiValued フィールド + 全文検索
# ---------------------------------------------------------------------------
def test_multivalued_filter_with_keyword():
    print("=== MultiValued: キーワード + フィルター ===")
    with _make_engine() as engine:
        # "Kyoto" + tags="Japan" → id=1,2
        results = engine.search("Kyoto", limit=10, filters={"tags": "Japan"})
        ids = {r.id for r in results}
        print(f"  Kyoto + tags=Japan: {sorted(ids)}")
        assert ids == {"1", "2"}, f"Unexpected: {ids}"

    print("✓ OK\n")


# ---------------------------------------------------------------------------
# Aggregation: aggregate_json() 低レベル API
# ---------------------------------------------------------------------------
def test_aggregate_json_all():
    print("=== aggregate_json: tags 全件集計 ===")
    with _make_engine() as engine:
        response = engine.aggregate_json({"name": "tags", "field": "tags", "size": 10})
        buckets = response["aggregations"]["tags"]["buckets"]
        bucket_map = {b["key"]: b["doc_count"] for b in buckets}
        print(f"  buckets: {bucket_map}")

        assert bucket_map.get("Japan")   == 4, f"Japan expected 4, got {bucket_map.get('Japan')}"
        assert bucket_map.get("city")    == 3, f"city expected 3, got {bucket_map.get('city')}"
        assert bucket_map.get("company") == 2, f"company expected 2, got {bucket_map.get('company')}"
        assert bucket_map.get("tourism") == 2, f"tourism expected 2, got {bucket_map.get('tourism')}"
        assert bucket_map.get("capital") == 1, f"capital expected 1, got {bucket_map.get('capital')}"
        assert bucket_map.get("France")  == 1, f"France expected 1, got {bucket_map.get('France')}"

    print("✓ OK\n")


# ---------------------------------------------------------------------------
# Aggregation: aggregate() 高レベル API
# ---------------------------------------------------------------------------
def test_aggregate_high_level():
    print("=== aggregate: 高レベル API ===")
    with _make_engine() as engine:
        # query="Kyoto" で絞り込み → Japan=2, city=1, ...
        response = engine.aggregate("tags", query="Kyoto", size=10)
        buckets = response["aggregations"]["tags"]["buckets"]
        bucket_map = {b["key"]: b["doc_count"] for b in buckets}
        print(f"  query=Kyoto buckets: {bucket_map}")
        assert bucket_map.get("Japan") == 2, f"Japan expected 2, got {bucket_map.get('Japan')}"
        assert bucket_map.get("city")  == 1, f"city expected 1, got {bucket_map.get('city')}"

    print("✓ OK\n")


def test_aggregate_size_limit():
    print("=== aggregate: size 制限 ===")
    with _make_engine() as engine:
        response = engine.aggregate("tags", size=3)
        buckets = response["aggregations"]["tags"]["buckets"]
        print(f"  size=3 buckets: {[b['key'] for b in buckets]}")
        assert len(buckets) == 3, f"Expected 3 buckets, got {len(buckets)}"
        # 上位3件: Japan(4), city(3), そして company か tourism (どちらも 2)
        assert buckets[0]["key"] == "Japan", f"Expected Japan first, got {buckets[0]['key']}"
        assert buckets[1]["key"] == "city",  f"Expected city second, got {buckets[1]['key']}"
        assert buckets[2]["doc_count"] == 2, f"Expected third bucket doc_count=2, got {buckets[2]['doc_count']}"

    print("✓ OK\n")


# ---------------------------------------------------------------------------
# search_response_json: AND 条件検索
# ---------------------------------------------------------------------------
def test_search_response_json_and():
    print("=== search_response_json: tags AND 条件 ===")
    with _make_engine() as engine:
        # tags="Japan" AND tags="city" → id=1,3
        response = engine.search_response_json({
            "size": 10,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"tags": "Japan"}},
                        {"term": {"tags": "city"}},
                    ]
                }
            },
        })
        total = response["hits"]["total"]["value"]
        hit_ids = {h["_source"]["id"] for h in response["hits"]["hits"]}
        print(f"  Japan AND city: total={total}, ids={sorted(hit_ids)}")
        assert hit_ids == {"1", "3"}, f"Unexpected: {hit_ids}"

        # tags="Japan" AND tags="tourism" → id=1
        response = engine.search_response_json({
            "size": 10,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"tags": "Japan"}},
                        {"term": {"tags": "tourism"}},
                    ]
                }
            },
        })
        hit_ids = {h["_source"]["id"] for h in response["hits"]["hits"]}
        print(f"  Japan AND tourism: ids={sorted(hit_ids)}")
        assert hit_ids == {"1"}, f"Unexpected: {hit_ids}"

    print("✓ OK\n")


# ---------------------------------------------------------------------------
# search_json: OpenSearch Query DSL で SearchResult リストを返す
# ---------------------------------------------------------------------------
def test_search_json():
    print("=== search_json: SearchResult リスト ===")
    with _make_engine() as engine:
        results = engine.search_json({
            "size": 10,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"tags": "Japan"}},
                        {"term": {"tags": "city"}},
                    ]
                }
            },
        })
        from nlp4j_local_search import SearchResult
        assert all(isinstance(r, SearchResult) for r in results)
        ids = {r.id for r in results}
        print(f"  Japan AND city (SearchResult): {sorted(ids)}")
        assert ids == {"1", "3"}, f"Unexpected: {ids}"

    print("✓ OK\n")


# ---------------------------------------------------------------------------
# バリデーション: aggregate のエラー系
# ---------------------------------------------------------------------------
def test_aggregate_validation():
    print("=== aggregate: バリデーション ===")
    with _make_engine() as engine:
        try:
            engine.aggregate("", size=10)
            assert False, "Should have raised"
        except InvalidDocumentError as e:
            print(f"  空フィールド名エラー: {e}")
            assert "non-empty" in str(e).lower()

        try:
            engine.aggregate("tags", size=0)
            assert False, "Should have raised"
        except InvalidDocumentError as e:
            print(f"  size=0 エラー: {e}")
            assert "size" in str(e).lower()

    print("✓ OK\n")


if __name__ == "__main__":
    try:
        test_multivalued_filter_single()
        test_multivalued_filter_with_keyword()
        test_aggregate_json_all()
        test_aggregate_high_level()
        test_aggregate_size_limit()
        test_search_response_json_and()
        test_search_json()
        test_aggregate_validation()
        print("=" * 60)
        print("すべての新機能テストが成功しました！")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
