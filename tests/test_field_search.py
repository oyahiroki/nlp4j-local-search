"""
テスト:
  - キーワード検索 + フィールド絞り込み (Example03, 04 相当) → Lucene Query に統一
  - ベクトル検索 + フィールド絞り込み  (Example05 相当) → search_vector()
  - テキスト add() への fields 引数
  - バリデーション
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nlp4j_local_search import SearchEngine
from nlp4j_local_search.errors import InvalidDocumentError


# ---------------------------------------------------------------------------
# Example03 相当: フィールド検索のみ → Lucene keyword field query
# ---------------------------------------------------------------------------
def test_field_search_only():
    print("=== フィールド検索のみ ===")
    with SearchEngine("en") as engine:
        engine.add_json({"id": "1", "body": "Kyoto is a historic city in Japan.",   "category": "city",    "country": "Japan"})
        engine.add_json({"id": "2", "body": "Nintendo is headquartered in Kyoto.",  "category": "company", "country": "Japan"})
        engine.add_json({"id": "3", "body": "Tokyo is the capital city of Japan.",  "category": "city",    "country": "Japan"})
        engine.add_json({"id": "4", "body": "Paris is the capital city of France.", "category": "city",    "country": "France"})
        engine.add_json({"id": "5", "body": "Sony is a Japanese company.",          "category": "company", "country": "Japan"})
        engine.commit()

        results = engine.search("category:city", 10)
        ids = [r.id for r in results]
        print(f"  category=city: {ids}")
        assert set(ids) == {"1", "3", "4"}, f"Unexpected: {ids}"

        results = engine.search("category:company", 10)
        ids = [r.id for r in results]
        print(f"  category=company: {ids}")
        assert set(ids) == {"2", "5"}, f"Unexpected: {ids}"

        results = engine.search("country:France", 10)
        ids = [r.id for r in results]
        print(f"  country=France: {ids}")
        assert ids == ["4"], f"Unexpected: {ids}"

    print("✓ OK\n")


# ---------------------------------------------------------------------------
# Example04 相当: キーワード検索 + フィールド絞り込み → Lucene AND
# ---------------------------------------------------------------------------
def test_keyword_and_field_search():
    print("=== キーワード + フィールド検索 ===")
    with SearchEngine("en") as engine:
        engine.add_json({"id": "1", "text_en": "Kyoto is a historic city in Japan.",            "category": "city",    "country": "Japan"})
        engine.add_json({"id": "2", "text_en": "Nintendo is headquartered in Kyoto, Japan.",    "category": "company", "country": "Japan"})
        engine.add_json({"id": "3", "text_en": "Tokyo is the capital city of Japan.",           "category": "city",    "country": "Japan"})
        engine.add_json({"id": "4", "text_en": "Paris is the capital city of France.",          "category": "city",    "country": "France"})
        engine.add_json({"id": "5", "text_en": "Sony is a Japanese multinational company.",     "category": "company", "country": "Japan"})
        engine.commit()

        # "Kyoto" かつ category=company → id=2 のみ
        results = engine.search("text_en:Kyoto AND category:company", 10)
        ids = [r.id for r in results]
        print(f"  Kyoto + category=company: {ids}")
        assert ids == ["2"], f"Unexpected: {ids}"

        # "Japan" かつ category=city → id=1, 3
        results = engine.search("text_en:Japan AND category:city", 10)
        ids = [r.id for r in results]
        print(f"  Japan + category=city: {ids}")
        assert set(ids) == {"1", "3"}, f"Unexpected: {ids}"

        # "city" かつ category=city AND country=Japan → id=1, 3
        results = engine.search("text_en:city AND category:city AND country:Japan", 10)
        ids = [r.id for r in results]
        print(f"  city + category=city + country=Japan: {ids}")
        assert set(ids) == {"1", "3"}, f"Unexpected: {ids}"

        # match_all (category=city AND country=France) → id=4
        results = engine.search("category:city AND country:France", 10)
        ids = [r.id for r in results]
        print(f"  category=city + country=France: {ids}")
        assert ids == ["4"], f"Unexpected: {ids}"

        # フィルターに一致なし
        results = engine.search("text_en:Tokyo AND country:France", 10)
        ids = [r.id for r in results]
        print(f"  Tokyo + country=France (0件): {ids}")
        assert ids == [], f"Unexpected: {ids}"

    print("✓ OK\n")


# ---------------------------------------------------------------------------
# add() の fields 引数 (テキスト文書)
# ---------------------------------------------------------------------------
def test_add_with_fields_text():
    print("=== add() fields (テキスト) ===")
    with SearchEngine("en") as engine:
        engine.add("1", "Kyoto is a historic city in Japan.",   fields={"category": "city",    "country": "Japan"})
        engine.add("2", "Nintendo is headquartered in Kyoto.",  fields={"category": "company", "country": "Japan"})
        engine.add("3", "Paris is the capital city of France.", fields={"category": "city",    "country": "France"})
        engine.commit()

        results = engine.search("text_en:Kyoto AND category:city", 10)
        ids = [r.id for r in results]
        print(f"  Kyoto + category=city: {ids}")
        assert ids == ["1"], f"Unexpected: {ids}"

    print("✓ OK\n")


# ---------------------------------------------------------------------------
# Example05 相当: ベクトル検索 + フィールド絞り込み → search_vector()
# ---------------------------------------------------------------------------
def test_vector_and_field_search():
    print("=== ベクトル + フィールド検索 ===")
    with SearchEngine("en", vector_dimension=2) as engine:
        engine.add("1_tech_East",   [ 1.0,  0.0], fields={"category": "tech",   "country": "Japan"})
        engine.add("2_tech_North",  [ 0.0,  1.0], fields={"category": "tech",   "country": "Japan"})
        engine.add("3_travel_East", [ 0.9,  0.2], fields={"category": "travel", "country": "Japan"})
        engine.add("4_travel_West", [-1.0,  0.0], fields={"category": "travel", "country": "France"})
        engine.add("5_tech_NE",     [ 0.7,  0.7], fields={"category": "tech",   "country": "USA"})
        engine.add("6_travel_NE",   [ 0.6,  0.8], fields={"category": "travel", "country": "Japan"})
        engine.commit()

        query = [0.9, 0.1]

        # フィルターなし: 6件すべて
        results = engine.search_vector(query, limit=6)
        ids = [r.id for r in results]
        print(f"  フィルターなし: {ids}")
        assert len(ids) == 6, f"Unexpected count: {len(ids)}"

        # category=tech: 3件、かつ先頭は 1_tech_East
        results = engine.search_vector(query, limit=6, filters={"category": "tech"})
        ids = [r.id for r in results]
        print(f"  category=tech: {ids}")
        assert len(ids) == 3, f"Unexpected count: {len(ids)}"
        assert ids[0] == "1_tech_East", f"Expected 1_tech_East first, got {ids[0]}"

        # category=travel: 3件
        results = engine.search_vector(query, limit=6, filters={"category": "travel"})
        ids = [r.id for r in results]
        print(f"  category=travel: {ids}")
        assert len(ids) == 3, f"Unexpected count: {len(ids)}"

        # category=tech + country=Japan: 2件 (5_tech_NE は USA)
        results = engine.search_vector(query, limit=6, filters={"category": "tech", "country": "Japan"})
        ids = [r.id for r in results]
        print(f"  category=tech + country=Japan: {ids}")
        assert set(ids) == {"1_tech_East", "2_tech_North"}, f"Unexpected: {ids}"

        # フィルターに一致なし
        results = engine.search_vector(query, limit=6, filters={"category": "tech", "country": "France"})
        ids = [r.id for r in results]
        print(f"  category=tech + country=France (0件): {ids}")
        assert ids == [], f"Unexpected: {ids}"

    print("✓ OK\n")


# ---------------------------------------------------------------------------
# バリデーション: fields に予約語
# ---------------------------------------------------------------------------
def test_validation_reserved_fields():
    print("=== バリデーション: 予約フィールド名 ===")
    with SearchEngine("en", vector_dimension=2) as engine:
        try:
            engine.add("1", [1.0, 0.0], fields={"id": "bad"})
            assert False, "Should have raised"
        except InvalidDocumentError as e:
            print(f"  期待通りのエラー: {e}")
            assert "reserved" in str(e).lower()

        try:
            engine.add("1", [1.0, 0.0], fields={"body": "bad"})
            assert False, "Should have raised"
        except InvalidDocumentError as e:
            print(f"  期待通りのエラー: {e}")
            assert "reserved" in str(e).lower()

    print("✓ OK\n")


# ---------------------------------------------------------------------------
# バリデーション: dict + fields の同時指定
# ---------------------------------------------------------------------------
def test_validation_dict_with_fields():
    print("=== バリデーション: dict + fields 同時指定 ===")
    with SearchEngine("en") as engine:
        try:
            engine.add({"id": "1", "body": "test"}, fields={"category": "x"})
            assert False, "Should have raised"
        except InvalidDocumentError as e:
            print(f"  期待通りのエラー: {e}")
            assert "fields cannot be used" in str(e).lower()

    print("✓ OK\n")


# ---------------------------------------------------------------------------
# バリデーション: limit < 1
# ---------------------------------------------------------------------------
def test_validation_limit():
    print("=== バリデーション: limit < 1 ===")
    with SearchEngine("en") as engine:
        engine.add("1", "test")
        engine.commit()
        try:
            engine.search("test", 0)
            assert False, "Should have raised"
        except InvalidDocumentError as e:
            print(f"  期待通りのエラー: {e}")
            assert "limit" in str(e).lower()

    print("✓ OK\n")


if __name__ == "__main__":
    try:
        test_field_search_only()
        test_keyword_and_field_search()
        test_add_with_fields_text()
        test_vector_and_field_search()
        test_validation_reserved_fields()
        test_validation_dict_with_fields()
        test_validation_limit()
        print("=" * 60)
        print("すべての新機能テストが成功しました！")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
