# example_007_multivalued_filter.py
#
# MultiValued フィールドに対するフィルター検索の例
#
# add_json() で JSON 配列を持つフィールドを登録すると、各要素が個別の
# keyword 値としてインデックスされます（MultiValued keyword field）。
#
# Lucene Query 構文でフィールドを指定してフィルター検索できます。
#
# ドキュメントのイメージ:
#   id=1  body="Kyoto is a historic city."              tags=["city","tourism","Japan"]
#   id=2  body="Nintendo is headquartered in Kyoto."    tags=["company","Japan"]
#   id=3  body="Tokyo is the capital city of Japan."    tags=["city","capital","Japan"]
#   id=4  body="Paris is a beautiful city in France."   tags=["city","tourism","France"]
#   id=5  body="Sony is a Japanese company in Tokyo."   tags=["company","Japan"]
#
# 単一値フィルターの期待結果:
#   tags:Japan   → id=1,2,3,5  (4件)
#   tags:city    → id=1,3,4    (3件)
#   tags:tourism → id=1,4      (2件)
#   tags:capital → id=3        (1件)
#   tags:sports  → 0件

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
    print('=== 1. Field filter: tags:Japan ===')
    for r in engine.search("tags:Japan", 10):
        print(f"  [{r.id}] {r.body}")

    print('=== 2. Field filter: tags:city ===')
    for r in engine.search("tags:city", 10):
        print(f"  [{r.id}] {r.body}")

    print('=== 3. Field filter: tags:tourism ===')
    for r in engine.search("tags:tourism", 10):
        print(f"  [{r.id}] {r.body}")

    print('=== 4. Field filter: tags:capital ===')
    for r in engine.search("tags:capital", 10):
        print(f"  [{r.id}] {r.body}")

    # --- 2. 全文検索 ＋ MultiValued フィールドフィルター ---
    print('=== 5. Keyword + field: text_en:Kyoto AND tags:Japan ===')
    for r in engine.search("text_en:Kyoto AND tags:Japan", 10):
        print(f"  [{r.id}] {r.body}")

    print('=== 6. Keyword + field: text_en:Japan AND tags:city ===')
    for r in engine.search("text_en:Japan AND tags:city", 10):
        print(f"  [{r.id}] {r.body}")

    print('=== 7. Keyword + field: text_en:Tokyo AND tags:company ===')
    for r in engine.search("text_en:Tokyo AND tags:company", 10):
        print(f"  [{r.id}] {r.body}")

    # --- 3. 同一フィールドへの AND 条件（search_response_json を使用）---
    #        Lucene Query の tags:Japan AND tags:city は単一フィールドの AND として
    #        機能しないため、bool/filter に複数 term を並べる方式を使う。
    print('=== 8. AND filter: tags:Japan AND tags:city ===')
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

    print('=== 9. AND filter: tags:Japan AND tags:tourism ===')
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
    print('=== 10. Field filter: tags:sports (no results) ===')
    results = engine.search("tags:sports", 10)
    print(f"  hits: {len(results)}")

# expected result
#
# === 1. Field filter: tags:Japan ===
#   [1] Kyoto is a historic city.
#   [2] Nintendo is headquartered in Kyoto.
#   [3] Tokyo is the capital city of Japan.
#   [5] Sony is a Japanese company based in Tokyo.
# === 2. Field filter: tags:city ===
#   [1] Kyoto is a historic city.
#   [3] Tokyo is the capital city of Japan.
#   [4] Paris is a beautiful city in France.
# === 3. Field filter: tags:tourism ===
#   [1] Kyoto is a historic city.
#   [4] Paris is a beautiful city in France.
# === 4. Field filter: tags:capital ===
#   [3] Tokyo is the capital city of Japan.
# === 5. Keyword + field: text_en:Kyoto AND tags:Japan ===
#   [1] Kyoto is a historic city.
#   [2] Nintendo is headquartered in Kyoto.
# === 6. Keyword + field: text_en:Japan AND tags:city ===
#   [3] Tokyo is the capital city of Japan.
# === 7. Keyword + field: text_en:Tokyo AND tags:company ===
#   [5] Sony is a Japanese company based in Tokyo.
# === 8. AND filter: tags:Japan AND tags:city ===
#   hits: 2
#   [1]
#   [3]
# === 9. AND filter: tags:Japan AND tags:tourism ===
#   hits: 1
#   [1]
# === 10. Field filter: tags:sports (no results) ===
#   hits: 0
