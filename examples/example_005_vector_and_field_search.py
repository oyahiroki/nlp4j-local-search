#
# ベクトル検索 ＋ フィールド絞り込みの例
#
# add(id, vector, fields=...) でベクトルと追加フィールドを同一ドキュメントに登録し、
# search_vector(vector, limit, filters=...) でフィールドフィルター付きの KNN 検索を行う例です。
#
# フィルターは後処理ではなく KNN クエリの内部で適用されます。
# そのため、フィルター条件を満たすドキュメントの中から真の上位 k 件が返ります。

from nlp4j_local_search import SearchEngine

documents = [
    {
        "id": "1_tech_East",
        "vector": [1.0, 0.0],
        "category": "tech",
        "country": "Japan",
    },
    {
        "id": "2_tech_North",
        "vector": [0.0, 1.0],
        "category": "tech",
        "country": "Japan",
    },
    {
        "id": "3_travel_East",
        "vector": [0.9, 0.2],
        "category": "travel",
        "country": "Japan",
    },
    {
        "id": "4_travel_West",
        "vector": [-1.0, 0.0],
        "category": "travel",
        "country": "France",
    },
    {
        "id": "5_tech_NE",
        "vector": [0.7, 0.7],
        "category": "tech",
        "country": "USA",
    },
    {
        "id": "6_travel_NE",
        "vector": [0.6, 0.8],
        "category": "travel",
        "country": "Japan",
    },
]

# --- データ表示 ---
print("=== Data ===")
for doc in documents:
    print(doc)

print()

with SearchEngine("en", vector_dimension=2) as engine:

    # --- ドキュメント登録 ---
    for doc in documents:
        engine.add(
            doc["id"],
            doc["vector"],
            fields={
                "category": doc["category"],
                "country": doc["country"],
            },
        )

    engine.commit()

    query_vector = [0.9, 0.1]

    # --- フィルターなし ---
    print(f"=== Vector search (no filter): queryVector={query_vector} ===")
    for r in engine.search_vector(query_vector, limit=6):
        print(f"  [{r.id}] score={r.score:.4f}")

    # --- 単一フィールドフィルター ---
    print("=== search_vector + category:tech ===")
    for r in engine.search_vector(
        query_vector,
        limit=6,
        filters={"category": "tech"},
    ):
        print(f"  [{r.id}] score={r.score:.4f}")

    print("=== search_vector + category:travel ===")
    for r in engine.search_vector(
        query_vector,
        limit=6,
        filters={"category": "travel"},
    ):
        print(f"  [{r.id}] score={r.score:.4f}")

    # --- 複数フィールドフィルター（AND） ---
    print("=== search_vector + category:tech + country:Japan ===")
    for r in engine.search_vector(
        query_vector,
        limit=6,
        filters={
            "category": "tech",
            "country": "Japan",
        },
    ):
        print(f"  [{r.id}] score={r.score:.4f}")

    # --- フィルターに一致なし ---
    print("=== search_vector + category:tech + country:France (no results) ===")
    results = engine.search_vector(
        query_vector,
        limit=6,
        filters={
            "category": "tech",
            "country": "France",
        },
    )
    print(f"  hits: {len(results)}")