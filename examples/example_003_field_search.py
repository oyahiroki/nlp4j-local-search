#
# フィールド検索の例
#
# add_json() で category / country などの追加フィールドを持つドキュメントを登録し、
# search() に Lucene Query 構文でフィールド完全一致による絞り込みを行う例です。
#
# keyword フィールドの絞り込み: field:value
# 複数フィールドの AND 条件:   field1:val1 AND field2:val2

from nlp4j_local_search import SearchEngine

documents = [
    {
        "id": "1",
        "body": "Kyoto is a historic city in Japan.",
        "category": "city",
        "country": "Japan",
    },
    {
        "id": "2",
        "body": "Nintendo is headquartered in Kyoto, Japan.",
        "category": "company",
        "country": "Japan",
    },
    {
        "id": "3",
        "body": "Tokyo is the capital city of Japan.",
        "category": "city",
        "country": "Japan",
    },
    {
        "id": "4",
        "body": "Paris is the capital city of France.",
        "category": "city",
        "country": "France",
    },
    {
        "id": "5",
        "body": "Sony is a Japanese multinational company.",
        "category": "company",
        "country": "Japan",
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

    # --- category フィールドで絞り込み ---
    print("=== Field search: category:city ===")
    for r in engine.search("category:city", 10):
        print(f"  [{r.id}] {r.body}")

    print("=== Field search: category:company ===")
    for r in engine.search("category:company", 10):
        print(f"  [{r.id}] {r.body}")

    # --- country フィールドで絞り込み ---
    print("=== Field search: country:Japan ===")
    for r in engine.search("country:Japan", 10):
        print(f"  [{r.id}] {r.body}")

    print("=== Field search: country:France ===")
    for r in engine.search("country:France", 10):
        print(f"  [{r.id}] {r.body}")

    # --- 複数フィールドの AND 条件 ---
    print("=== Field search: category:city AND country:Japan ===")
    for r in engine.search("category:city AND country:Japan", 10):
        print(f"  [{r.id}] {r.body}")

    # --- 存在しない値 ---
    print("=== Field search: category:sports (no results) ===")
    results = engine.search("category:sports", 10)
    print(f"  hits: {len(results)}")