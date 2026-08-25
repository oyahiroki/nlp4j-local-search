# example_003_field_search.py
#
# フィールド検索の例
#
# addJson() で category / country などの追加フィールドを持つドキュメントを登録し、
# search() に Lucene Query 構文でフィールド完全一致による絞り込みを行う例です。
#
# keyword フィールドの絞り込み: field:value
# 複数フィールドの AND 条件:   field1:val1 AND field2:val2

from nlp4j_local_search import SearchEngine

with SearchEngine("en") as engine:

    # ドキュメント登録（id, body, 追加フィールド）
    engine.add_json({"id": "1", "body": "Kyoto is a historic city in Japan.",
                     "category": "city",    "country": "Japan"})
    engine.add_json({"id": "2", "body": "Nintendo is headquartered in Kyoto, Japan.",
                     "category": "company", "country": "Japan"})
    engine.add_json({"id": "3", "body": "Tokyo is the capital city of Japan.",
                     "category": "city",    "country": "Japan"})
    engine.add_json({"id": "4", "body": "Paris is the capital city of France.",
                     "category": "city",    "country": "France"})
    engine.add_json({"id": "5", "body": "Sony is a Japanese multinational company.",
                     "category": "company", "country": "Japan"})
    engine.commit()

    # --- category フィールドで絞り込み ---
    print('=== Field search: category:city ===')
    for r in engine.search("category:city", 10):
        print(f"  [{r.id}] {r.body}")

    print('=== Field search: category:company ===')
    for r in engine.search("category:company", 10):
        print(f"  [{r.id}] {r.body}")

    # --- country フィールドで絞り込み ---
    print('=== Field search: country:Japan ===')
    for r in engine.search("country:Japan", 10):
        print(f"  [{r.id}] {r.body}")

    print('=== Field search: country:France ===')
    for r in engine.search("country:France", 10):
        print(f"  [{r.id}] {r.body}")

    # --- 存在しない値 ---
    print('=== Field search: category:sports (no results) ===')
    results = engine.search("category:sports", 10)
    print(f"  hits: {len(results)}")

# expected result

# === Field search: category:city ===
#   [1] Kyoto is a historic city in Japan.
#   [3] Tokyo is the capital city of Japan.
#   [4] Paris is the capital city of France.
# === Field search: category:company ===
#   [2] Nintendo is headquartered in Kyoto, Japan.
#   [5] Sony is a Japanese multinational company.
# === Field search: country:Japan ===
#   [1] Kyoto is a historic city in Japan.
#   [2] Nintendo is headquartered in Kyoto, Japan.
#   [3] Tokyo is the capital city of Japan.
#   [5] Sony is a Japanese multinational company.
# === Field search: country:France ===
#   [4] Paris is the capital city of France.
# === Field search: category:sports (no results) ===
#   hits: 0
