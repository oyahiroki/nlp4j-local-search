"""ベクトル検索の使用例"""
from nlp4j_local_search import SearchEngine

documents = [
    {"id": "1_East", "vector": [1.0, 0.0]},
    {"id": "2_North", "vector": [0.0, 1.0]},
    {"id": "3_West", "vector": [-1.0, 0.0]},
    {"id": "4_South", "vector": [0.0, -1.0]},
]

print("=== データ ===")
for doc in documents:
    print(doc)

print()

print("=== ベクトル検索の例 ===")

# 2次元ベクトル空間でのベクトル検索
with SearchEngine("ja", vector_dimension=2) as engine:

    # ベクトルを追加
    for doc in documents:
        engine.add(doc["id"], doc["vector"])

    engine.commit()

    # 東寄りのベクトルで検索
    query_vector = [0.9, 0.1]
    print(f"クエリベクトル: {query_vector}")

    for r in engine.search_vector(query_vector, limit=10):
        print(f"  {r.id}: body={r.body} (score: {r.score})")

print("\n完了！")

