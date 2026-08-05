# example_004_keyword_and_field_search.py
#
# キーワード検索 ＋ フィールド絞り込みの例
#
# search(query, limit, filters=...) で全文検索とフィールド絞り込みを同時に行う例です。
#
# - query が空文字列の場合は match_all（全件）として扱われます
# - filters に複数フィールドを指定した場合は AND 条件になります
# - フィールドのスコアへの影響はありません（スコアはキーワード一致度のみ）

from nlp4j_local_search import SearchEngine

with SearchEngine("en") as engine:

    # ドキュメント登録
    engine.add_json({"id": "1", "body": "Kyoto is a historic city in Japan.",
                     "category": "city",    "country": "Japan"})
    engine.add_json({"id": "2", "body": "Nintendo is headquartered in Kyoto, Japan.",
                     "category": "company", "country": "Japan"})
    engine.add_json({"id": "3", "body": "Tokyo is the capital city of Japan.",
                     "category": "city",    "country": "Japan"})
    engine.add_json({"id": "4", "body": "Paris is the capital city of France.",
                     "category": "city",    "country": "France"})
    engine.add_json({"id": "5", "body": "Sony is a Japanese multinational company based in Tokyo.",
                     "category": "company", "country": "Japan"})
    engine.commit()

    # --- キーワード + 単一フィールド絞り込み ---
    print('=== Keyword + field: "Kyoto" + category="company" ===')
    for r in engine.search("Kyoto", limit=10, filters={"category": "company"}):
        print(f"  [{r.id}] score={r.score:.4f}  {r.body}")

    print('=== Keyword + field: "Japan" + category="city" ===')
    for r in engine.search("Japan", limit=10, filters={"category": "city"}):
        print(f"  [{r.id}] score={r.score:.4f}  {r.body}")

    # --- キーワード + 複数フィールド絞り込み（AND） ---
    print('=== Keyword + field: "city" + category="city" + country="Japan" ===')
    for r in engine.search("city", limit=10, filters={"category": "city", "country": "Japan"}):
        print(f"  [{r.id}] score={r.score:.4f}  {r.body}")

    # --- クエリなし（match_all）+ フィールド絞り込み ---
    print('=== match_all + category="city" + country="France" ===')
    for r in engine.search("", limit=10, filters={"category": "city", "country": "France"}):
        print(f"  [{r.id}] score={r.score:.4f}  {r.body}")

    # --- フィルターに一致なし ---
    print('=== Keyword + field: "Tokyo" + country="France" (no results) ===')
    results = engine.search("Tokyo", limit=10, filters={"country": "France"})
    print(f"  hits: {len(results)}")

# expected result

# === Keyword + field: "Kyoto" + category="company" ===
#   [2] score=0.xxxx  Nintendo is headquartered in Kyoto, Japan.
# === Keyword + field: "Japan" + category="city" ===
#   [1] score=0.xxxx  Kyoto is a historic city in Japan.
#   [3] score=0.xxxx  Tokyo is the capital city of Japan.
# === Keyword + field: "city" + category="city" + country="Japan" ===
#   [1] score=0.xxxx  Kyoto is a historic city in Japan.
#   [3] score=0.xxxx  Tokyo is the capital city of Japan.
# === match_all + category="city" + country="France" ===
#   [4] score=0.xxxx  Paris is the capital city of France.
# === Keyword + field: "Tokyo" + country="France" (no results) ===
#   hits: 0
