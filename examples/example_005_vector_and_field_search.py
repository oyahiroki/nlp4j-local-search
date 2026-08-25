# example_005_vector_and_field_search.py
#
# ベクトル検索 ＋ フィールド絞り込みの例
#
# add(id, vector, fields=...) でベクトルと追加フィールドを同一ドキュメントに登録し、
# search_vector(vector, limit, filters=...) でフィールドフィルター付きの KNN 検索を行う例です。
#
# フィルターは後処理ではなく KNN クエリの内部で適用されます。
# そのため、フィルター条件を満たすドキュメントの中から真の上位 k 件が返ります。
#
# ベクトルのイメージ（2次元）:
#
#   id=1_tech_East   category=tech   ( 1.0,  0.0)
#   id=2_tech_North  category=tech   ( 0.0,  1.0)
#   id=3_travel_East category=travel ( 0.9,  0.2)  ← クエリに最近傍だが travel
#   id=4_travel_West category=travel (-1.0,  0.0)
#   id=5_tech_NE     category=tech   ( 0.7,  0.7)
#   id=6_travel_NE   category=travel ( 0.6,  0.8)
#
# クエリ (0.9, 0.1):
#   フィルターなし → id=3, id=1, id=5, ... の順
#   category=tech  → id=1, id=5, id=2, ... の順（travel を除外した近傍）

from nlp4j_local_search import SearchEngine

with SearchEngine("en", vector_dimension=2) as engine:

    # ドキュメント登録（id, vector, fields）
    engine.add("1_tech_East",   [ 1.0,  0.0], fields={"category": "tech",   "country": "Japan"})
    engine.add("2_tech_North",  [ 0.0,  1.0], fields={"category": "tech",   "country": "Japan"})
    engine.add("3_travel_East", [ 0.9,  0.2], fields={"category": "travel", "country": "Japan"})
    engine.add("4_travel_West", [-1.0,  0.0], fields={"category": "travel", "country": "France"})
    engine.add("5_tech_NE",     [ 0.7,  0.7], fields={"category": "tech",   "country": "USA"})
    engine.add("6_travel_NE",   [ 0.6,  0.8], fields={"category": "travel", "country": "Japan"})
    engine.commit()

    query_vector = [0.9, 0.1]

    # --- フィルターなし ---
    print(f"=== Vector search (no filter): queryVector={query_vector} ===")
    for r in engine.search_vector(query_vector, limit=6):
        print(f"  [{r.id}]  score={r.score:.4f}")

    # --- 単一フィールドフィルター ---
    print(f'=== search_vector + category:tech ===')
    for r in engine.search_vector(query_vector, limit=6, filters={"category": "tech"}):
        print(f"  [{r.id}]  score={r.score:.4f}")

    print(f'=== search_vector + category:travel ===')
    for r in engine.search_vector(query_vector, limit=6, filters={"category": "travel"}):
        print(f"  [{r.id}]  score={r.score:.4f}")

    # --- 複数フィールドフィルター（AND） ---
    print(f'=== search_vector + category:tech + country:Japan ===')
    for r in engine.search_vector(query_vector, limit=6, filters={"category": "tech", "country": "Japan"}):
        print(f"  [{r.id}]  score={r.score:.4f}")

    # --- フィルターに一致なし ---
    print(f'=== search_vector + category:tech + country:France (no results) ===')
    results = engine.search_vector(query_vector, limit=6, filters={"category": "tech", "country": "France"})
    print(f"  hits: {len(results)}")

# expected result

# === Vector search (no filter): queryVector=[0.9, 0.1] ===
#   [3_travel_East]  score=0.xxxx   ← フィルターなしでは travel が最近傍
#   [1_tech_East]    score=0.xxxx
#   [5_tech_NE]      score=0.xxxx
#   [6_travel_NE]    score=0.xxxx
#   [2_tech_North]   score=0.xxxx
#   [4_travel_West]  score=0.xxxx
# === search_vector + category:tech ===
#   [1_tech_East]    score=0.xxxx   ← tech の中での最近傍
#   [5_tech_NE]      score=0.xxxx
#   [2_tech_North]   score=0.xxxx
# === search_vector + category:travel ===
#   [3_travel_East]  score=0.xxxx
#   [6_travel_NE]    score=0.xxxx
#   [4_travel_West]  score=0.xxxx
# === search_vector + category:tech + country:Japan ===
#   [1_tech_East]    score=0.xxxx
#   [2_tech_North]   score=0.xxxx
# === search_vector + category:tech + country:France (no results) ===
#   hits: 0
