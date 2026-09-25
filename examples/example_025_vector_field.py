#
# example_025_vector_field.py
#
# 任意名 KNN ベクトルフィールドの定義・登録・検索の例
#
# Java 版 Example25_VectorField.java の Python 版です。
#
# デモする内容:
#   1. VectorFieldConfig で任意名ベクトルフィールドを定義
#   2. add_json() でベクトル値を JSON から登録
#   3. field_info() でフィールドメタデータを確認
#   4. search_vector(field=...) で KNN ベクトル検索
#   5. search_vector(field=..., filter_query=...) で Lucene クエリフィルター付き検索
#
# 3次元ベクトルを使うため、Embedding モデルなしで動作します。

from nlp4j_local_search import SearchEngine, VectorFieldConfig

# ------------------------------------------------------------
# 1. ベクトルフィールドを定義してエンジンを構築
#
#    "vector3": 3次元、コサイン類似度、モデル名 "demo-3d"
# ------------------------------------------------------------

with SearchEngine(
    lang="en",
    vector_fields={
        "vector3": VectorFieldConfig(
            dimension=3,
            similarity="cosine",
            model="demo-3d",
        )
    },
) as engine:

    # ------------------------------------------------------------
    # 2. ドキュメントを登録
    #
    #    vector3 は schema で KNN_VECTOR と定義済み。
    #    category_s は値から自動的に KEYWORD フィールドと判定される。
    # ------------------------------------------------------------

    engine.add_json({
        "id": "1",
        "text_en": "Electric vehicle battery",
        "category_s": "vehicle",
        "vector3": [1.0, 0.0, 0.0],
    })

    engine.add_json({
        "id": "2",
        "text_en": "Hybrid vehicle system",
        "category_s": "vehicle",
        "vector3": [0.9, 0.1, 0.0],
    })

    engine.add_json({
        "id": "3",
        "text_en": "Computer software",
        "category_s": "software",
        "vector3": [0.0, 1.0, 0.0],
    })

    engine.add_json({
        "id": "4",
        "text_en": "Cloud computing service",
        "category_s": "software",
        "vector3": [0.0, 0.9, 0.1],
    })

    engine.commit()

    # ------------------------------------------------------------
    # 3. フィールドメタデータを確認
    # ------------------------------------------------------------

    print("=== Vector field metadata ===")

    info = engine.field_info("vector3")

    print(f"Type      : {info.type}")
    print(f"Dimension : {info.dimension}")
    print(f"Model     : {info.model}")

    print()

    # ------------------------------------------------------------
    # 4. ベクトル検索
    #
    #    クエリベクトルは (1, 0, 0) — doc1, doc2 に近い
    # ------------------------------------------------------------

    query_vector = [1.0, 0.0, 0.0]

    print(f"=== Vector search: vector3, query={query_vector} ===")

    for r in engine.search_vector(query_vector, field="vector3", limit=10):
        print(f"  id={r.id}  score={r.score:.4f}  body={r.body}")

    print()

    # ------------------------------------------------------------
    # 5. Lucene クエリフィルター付きベクトル検索
    #
    #    category_s="vehicle" の文書のみを対象に検索する。
    #    フィルターは KNN クエリ内部で適用されるため、
    #    "vehicle" 文書の中から真の上位 k 件が返る。
    # ------------------------------------------------------------

    print('=== Vector search: filter_query=\'category_s:"vehicle"\' ===')

    for r in engine.search_vector(
        query_vector,
        field="vector3",
        limit=10,
        filter_query='category_s:"vehicle"',
    ):
        print(f"  id={r.id}  score={r.score:.4f}  body={r.body}")

    print()

    # ------------------------------------------------------------
    # 6. 別方向のクエリベクトル
    #
    #    (0, 1, 0) — doc3, doc4 (software) に近い
    # ------------------------------------------------------------

    software_vector = [0.0, 1.0, 0.0]

    print(f"=== Vector search: software direction, query={software_vector} ===")

    for r in engine.search_vector(software_vector, field="vector3", limit=10):
        print(f"  id={r.id}  score={r.score:.4f}  body={r.body}")

    print()

    # ------------------------------------------------------------
    # 7. vector_fields() で VECTOR フィールド一覧を確認
    # ------------------------------------------------------------

    print("=== Vector fields ===")
    print(engine.vector_fields())


# expected output
#
# === Vector field metadata ===
# Type      : VECTOR
# Dimension : 3
# Model     : demo-3d
#
# === Vector search: vector3, query=[1.0, 0.0, 0.0] ===
#   id=1  score=1.0000  body=...
#   id=2  score=...     body=...
#   id=3  score=...     body=...
#   id=4  score=...     body=...
#
# === Vector search: filter_query='category_s:"vehicle"' ===
#   id=1  score=1.0000  body=...
#   id=2  score=...     body=...
#
# === Vector search: software direction, query=[0.0, 1.0, 0.0] ===
#   id=3  score=1.0000  body=...
#   id=4  score=...     body=...
#   id=1  score=...     body=...
#   id=2  score=...     body=...
#
# === Vector fields ===
# ['vector3']
