#
# キーワード検索 ＋ フィールド絞り込みの例
#
# search() に Lucene Query 構文で全文検索とフィールド絞り込みを同時に行う例です。
#
# テキストフィールド（"en" エンジン）: text_en:keyword
# keyword フィールド:                  field:value
# AND 結合:                            text_en:Kyoto AND category:company

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
        "body": "Sony is a Japanese multinational company based in Tokyo.",
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

    # --- キーワード + 単一フィールド絞り込み ---
    print("=== text_en:Kyoto AND category:company ===")
    for r in engine.search("text_en:Kyoto AND category:company", 10):
        print(f"  [{r.id}] score={r.score:.4f}  {r.body}")

    print("=== text_en:Japan AND category:city ===")
    for r in engine.search("text_en:Japan AND category:city", 10):
        print(f"  [{r.id}] score={r.score:.4f}  {r.body}")

    # --- キーワード + 複数フィールド絞り込み（AND） ---
    print("=== text_en:city AND category:city AND country:Japan ===")
    for r in engine.search(
        "text_en:city AND category:city AND country:Japan", 10
    ):
        print(f"  [{r.id}] score={r.score:.4f}  {r.body}")

    # --- フィールドのみ + 複数フィールド絞り込み ---
    print("=== category:city AND country:France ===")
    for r in engine.search("category:city AND country:France", 10):
        print(f"  [{r.id}] score={r.score:.4f}  {r.body}")

    # --- 一致なし ---
    print("=== text_en:Tokyo AND country:France (no results) ===")
    results = engine.search("text_en:Tokyo AND country:France", 10)
    print(f"  hits: {len(results)}")