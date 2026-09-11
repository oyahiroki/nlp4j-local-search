#
# MultiValued フィールドに対するフィルター検索の例
#
# add_json() で JSON 配列を持つフィールドを登録すると、各要素が個別の
# keyword 値としてインデックスされます（MultiValued keyword field）。
#
# Lucene Query 構文でフィールドを指定してフィルター検索できます。
#

from nlp4j_local_search import SearchEngine

documents = [
    {
        "id": "1",
        "body": "Kyoto is a historic city.",
        "tags": ["city", "tourism", "Japan"],
    },
    {
        "id": "2",
        "body": "Nintendo is headquartered in Kyoto.",
        "tags": ["company", "Japan"],
    },
    {
        "id": "3",
        "body": "Tokyo is the capital city of Japan.",
        "tags": ["city", "capital", "Japan"],
    },
    {
        "id": "4",
        "body": "Paris is a beautiful city in France.",
        "tags": ["city", "tourism", "France"],
    },
    {
        "id": "5",
        "body": "Sony is a Japanese company based in Tokyo.",
        "tags": ["company", "Japan"],
    },
]

# --- データ表示 ---
print("=== Data ===")
for doc in documents:
    print(doc)

print()

with SearchEngine("en") as engine:

    # --- ドキュメント登録 ---
    for doc in documents:
        engine.add_json(doc)

    engine.commit()

    # --- 1. MultiValued フィールドの単一値フィルター ---
    print("=== 1. Field filter: tags:Japan ===")
    for r in engine.search("tags:Japan", 10):
        print(f"  [{r.id}] {r.body}")

    print("=== 2. Field filter: tags:city ===")
    for r in engine.search("tags:city", 10):
        print(f"  [{r.id}] {r.body}")

    print("=== 3. Field filter: tags:tourism ===")
    for r in engine.search("tags:tourism", 10):
        print(f"  [{r.id}] {r.body}")

    print("=== 4. Field filter: tags:capital ===")
    for r in engine.search("tags:capital", 10):
        print(f"  [{r.id}] {r.body}")

    # --- 2. 全文検索 ＋ MultiValued フィールドフィルター ---
    print("=== 5. Keyword + field: text_en:Kyoto AND tags:Japan ===")
    for r in engine.search("text_en:Kyoto AND tags:Japan", 10):
        print(f"  [{r.id}] {r.body}")

    print("=== 6. Keyword + field: text_en:Japan AND tags:city ===")
    for r in engine.search("text_en:Japan AND tags:city", 10):
        print(f"  [{r.id}] {r.body}")

    print("=== 7. Keyword + field: text_en:Tokyo AND tags:company ===")
    for r in engine.search("text_en:Tokyo AND tags:company", 10):
        print(f"  [{r.id}] {r.body}")

    # --- 3. 同一フィールドへの AND 条件（search_response_json を使用） ---
    #
    # Lucene Query の tags:Japan AND tags:city は、
    # MultiValued フィールドに対する複数値 AND 条件としては扱わず、
    # bool/filter に複数の term 条件を並べる方式を使う。
    #
    print("=== 8. AND filter: tags:Japan AND tags:city ===")
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
    print(f"  hits: {total}")
    for hit in response["hits"]["hits"]:
        print(
            f"  [{hit['_source']['id']}] "
            f"{hit['_source']['body']}"
        )

    print("=== 9. AND filter: tags:Japan AND tags:tourism ===")
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

    total = response["hits"]["total"]["value"]
    print(f"  hits: {total}")
    for hit in response["hits"]["hits"]:
        print(
            f"  [{hit['_source']['id']}] "
            f"{hit['_source']['body']}"
        )

    # --- 4. 該当なしのケース ---
    print("=== 10. Field filter: tags:sports (no results) ===")
    results = engine.search("tags:sports", 10)

    print(f"  hits: {len(results)}")
    for r in results:
        print(f"  [{r.id}] {r.body}")


# expected result
#
# === Data ===
# {'id': '1', 'body': 'Kyoto is a historic city.', 'tags': ['city', 'tourism', 'Japan']}
# {'id': '2', 'body': 'Nintendo is headquartered in Kyoto.', 'tags': ['company', 'Japan']}
# {'id': '3', 'body': 'Tokyo is the capital city of Japan.', 'tags': ['city', 'capital', 'Japan']}
# {'id': '4', 'body': 'Paris is a beautiful city in France.', 'tags': ['city', 'tourism', 'France']}
# {'id': '5', 'body': 'Sony is a Japanese company based in Tokyo.', 'tags': ['company', 'Japan']}
#
# === 1. Field filter: tags:Japan ===
#   [1] Kyoto is a historic city.
#   [2] Nintendo is headquartered in Kyoto.
#   [3] Tokyo is the capital city of Japan.
#   [5] Sony is a Japanese company based in Tokyo.
#
# === 2. Field filter: tags:city ===
#   [1] Kyoto is a historic city.
#   [3] Tokyo is the capital city of Japan.
#   [4] Paris is a beautiful city in France.
#
# === 3. Field filter: tags:tourism ===
#   [1] Kyoto is a historic city.
#   [4] Paris is a beautiful city in France.
#
# === 4. Field filter: tags:capital ===
#   [3] Tokyo is the capital city of Japan.
#
# === 5. Keyword + field: text_en:Kyoto AND tags:Japan ===
#   [1] Kyoto is a historic city.
#   [2] Nintendo is headquartered in Kyoto.
#
# === 6. Keyword + field: text_en:Japan AND tags:city ===
#   [3] Tokyo is the capital city of Japan.
#
# === 7. Keyword + field: text_en:Tokyo AND tags:company ===
#   [5] Sony is a Japanese company based in Tokyo.
#
# === 8. AND filter: tags:Japan AND tags:city ===
#   hits: 2
#   [1] Kyoto is a historic city.
#   [3] Tokyo is the capital city of Japan.
#
# === 9. AND filter: tags:Japan AND tags:tourism ===
#   hits: 1
#   [1] Kyoto is a historic city.
#
# === 10. Field filter: tags:sports (no results) ===
#   hits: 0

