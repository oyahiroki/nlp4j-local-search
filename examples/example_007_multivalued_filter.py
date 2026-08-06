# example_007_multivalued_filter.py
#
# MultiValued フィールドに対するフィルター検索の例
#
# add_json() で JSON 配列を持つフィールドを登録すると、各要素が個別の
# keyword 値としてインデックスされます（MultiValued keyword field）。
#
# ドキュメントのイメージ:
#   id=1  body="Kyoto is a historic city."              tags=["city","tourism","Japan"]
#   id=2  body="Nintendo is headquartered in Kyoto."    tags=["company","Japan"]
#   id=3  body="Tokyo is the capital city of Japan."    tags=["city","capital","Japan"]
#   id=4  body="Paris is a beautiful city in France."   tags=["city","tourism","France"]
#   id=5  body="Sony is a Japanese company in Tokyo."   tags=["company","Japan"]
#
# 単一値フィルターの期待結果:
#   tags="Japan"   → id=1,2,3,5  (4件)
#   tags="city"    → id=1,3,4    (3件)
#   tags="tourism" → id=1,4      (2件)
#   tags="capital" → id=3        (1件)
#   tags="sports"  → 0件
#
# AND条件の期待結果:
#   tags="Japan" AND tags="city"    → id=1,3
#   tags="Japan" AND tags="tourism" → id=1

from nlp4j_local_search import SearchEngine

with SearchEngine("en") as engine:

    # ドキュメント登録（tags を JSON 配列で指定 → MultiValued keyword field）
    engine.add_json({"id": "1", "body": "Kyoto is a historic city.",
                     "tags": ["city", "tourism", "Japan"]})
    engine.add_json({"id": "2", "body": "Nintendo is headquartered in Kyoto.",
                     "tags": ["company", "Japan"]})
    engine.add_json({"id": "3", "body": "Tokyo is the capital city of Japan.",
                     "tags": ["city", "capital", "Japan"]})
    engine.add_json({"id": "4", "body": "Paris is a beautiful city in France.",
                     "tags": ["city", "tourism", "France"]})
    engine.add_json({"id": "5", "body": "Sony is a Japanese company based in Tokyo.",
                     "tags": ["company", "Japan"]})
    engine.commit()

    # --- 1. MultiValued フィールドの単一値フィルター ---
    print('=== 1. Field filter: tags="Japan" ===')
    for r in engine.search("", limit=10, filters={"tags": "Japan"}):
        print(f"  [{r.id}] {r.body}")

    print('=== 2. Field filter: tags="city" ===')
    for r in engine.search("", limit=10, filters={"tags": "city"}):
        print(f"  [{r.id}] {r.body}")

    print('=== 3. Field filter: tags="tourism" ===')
    for r in engine.search("", limit=10, filters={"tags": "tourism"}):
        print(f"  [{r.id}] {r.body}")

    print('=== 4. Field filter: tags="capital" ===')
    for r in engine.search("", limit=10, filters={"tags": "capital"}):
        print(f"  [{r.id}] {r.body}")

    # --- 2. 全文検索 ＋ MultiValued フィールドフィルター ---
    print('=== 5. Keyword + field: "Kyoto" + tags="Japan" ===')
    for r in engine.search("Kyoto", limit=10, filters={"tags": "Japan"}):
        print(f"  [{r.id}] {r.body}")

    print('=== 6. Keyword + field: "Japan" + tags="city" ===')
    for r in engine.search("Japan", limit=10, filters={"tags": "city"}):
        print(f"  [{r.id}] {r.body}")

    print('=== 7. Keyword + field: "Tokyo" + tags="company" ===')
    for r in engine.search("Tokyo", limit=10, filters={"tags": "company"}):
        print(f"  [{r.id}] {r.body}")

    # --- 3. 同一フィールドへの AND 条件（search_response_json を使用）---
    #        Python の dict は同一キーを複数持てないため、
    #        filters={"tags": "Japan", "tags": "city"} と書くと後者が上書きされる。
    #        bool/filter に複数 term を並べることで AND 条件を実現する。
    #        _source.id でドキュメント ID を、_source.data で登録した元 JSON を取得できる。
    print('=== 8. AND filter: tags="Japan" AND tags="city" ===')
    response = engine.search_response_json({
        "size": 10,
        "query": {"bool": {"filter": [
            {"term": {"tags": "Japan"}},
            {"term": {"tags": "city"}},
        ]}},
    })
    total = response["hits"]["total"]["value"]
    print(f"  hits: {total}")
    for hit in response["hits"]["hits"]:
        print(f"  [{hit['_source']['id']}]")

    print('=== 9. AND filter: tags="Japan" AND tags="tourism" ===')
    response = engine.search_response_json({
        "size": 10,
        "query": {"bool": {"filter": [
            {"term": {"tags": "Japan"}},
            {"term": {"tags": "tourism"}},
        ]}},
    })
    total = response["hits"]["total"]["value"]
    print(f"  hits: {total}")
    for hit in response["hits"]["hits"]:
        print(f"  [{hit['_source']['id']}]")

    # --- 4. 該当なしのケース ---
    print('=== 10. Field filter: tags="sports" (no results) ===')
    results = engine.search("", limit=10, filters={"tags": "sports"})
    print(f"  hits: {len(results)}")

# expected result
#
# === 1. Field filter: tags="Japan" ===
#   [1] Kyoto is a historic city.
#   [2] Nintendo is headquartered in Kyoto.
#   [3] Tokyo is the capital city of Japan.
#   [5] Sony is a Japanese company based in Tokyo.
# === 2. Field filter: tags="city" ===
#   [1] Kyoto is a historic city.
#   [3] Tokyo is the capital city of Japan.
#   [4] Paris is a beautiful city in France.
# === 3. Field filter: tags="tourism" ===
#   [1] Kyoto is a historic city.
#   [4] Paris is a beautiful city in France.
# === 4. Field filter: tags="capital" ===
#   [3] Tokyo is the capital city of Japan.
# === 5. Keyword + field: "Kyoto" + tags="Japan" ===
#   [1] Kyoto is a historic city.
#   [2] Nintendo is headquartered in Kyoto.
# === 6. Keyword + field: "Japan" + tags="city" ===
#   [3] Tokyo is the capital city of Japan.
# === 7. Keyword + field: "Tokyo" + tags="company" ===
#   [5] Sony is a Japanese company based in Tokyo.
# === 8. AND filter: tags="Japan" AND tags="city" ===
#   hits: 2
#   [1]
#   [3]
# === 9. AND filter: tags="Japan" AND tags="tourism" ===
#   hits: 1
#   [1]
# === 10. Field filter: tags="sports" (no results) ===
#   hits: 0
