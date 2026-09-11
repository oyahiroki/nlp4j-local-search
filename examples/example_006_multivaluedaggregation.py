#
# MultiValued フィールドの Aggregation（terms 集計）の例
#
# add_json() で JSON 配列を持つフィールドを登録すると、各要素が個別の
# keyword 値としてインデックスされます（MultiValued keyword field）。
# 1 つのドキュメントが複数の集計バケットにカウントされます。
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

    # --- 1. tags フィールドの全件集計 ---
    print("=== 1. tags 全件集計 ===")
    response = engine.aggregate("tags", size=10)
    for bucket in response["aggregations"]["tags"]["buckets"]:
        print(f"  {bucket['key']:10s}  doc_count={bucket['doc_count']}")

    # --- 2. query="Kyoto" で絞り込んだ上での tags 集計 ---
    print('=== 2. tags 集計（query="Kyoto" で絞り込み）===')
    response = engine.aggregate("tags", size=10, query="Kyoto")
    for bucket in response["aggregations"]["tags"]["buckets"]:
        print(f"  {bucket['key']:10s}  doc_count={bucket['doc_count']}")

    # --- 3. size=3 で上位 3 バケットのみ取得 ---
    print("=== 3. tags 集計（size=3、上位 3 件のみ）===")
    response = engine.aggregate("tags", size=3)
    for bucket in response["aggregations"]["tags"]["buckets"]:
        print(f"  {bucket['key']:10s}  doc_count={bucket['doc_count']}")