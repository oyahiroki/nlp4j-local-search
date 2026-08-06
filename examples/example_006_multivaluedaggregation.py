# example_006_multivaluedaggregation.py
#
# MultiValued フィールドの Aggregation（terms 集計）の例
#
# add_json() で JSON 配列を持つフィールドを登録すると、各要素が個別の
# keyword 値としてインデックスされます（MultiValued keyword field）。
# 1 つのドキュメントが複数の集計バケットにカウントされます。
#
# ドキュメントのイメージ:
#   id=1  body="Kyoto is a historic city."         tags=["city","tourism","Japan"]
#   id=2  body="Nintendo is headquartered in Kyoto." tags=["company","Japan"]
#   id=3  body="Tokyo is the capital city of Japan." tags=["city","capital","Japan"]
#   id=4  body="Paris is a beautiful city in France." tags=["city","tourism","France"]
#   id=5  body="Sony is a Japanese company in Tokyo." tags=["company","Japan"]
#
# 全件集計の期待結果（tags フィールド）:
#   Japan=4, city=3, company=2, tourism=2, capital=1, France=1

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

# expected result
#
# === 1. tags 全件集計 ===
#   Japan       doc_count=4
#   city        doc_count=3
#   tourism     doc_count=2
#   company     doc_count=2
#   capital     doc_count=1
#   France      doc_count=1
# === 2. tags 集計（query="Kyoto" で絞り込み）===
#   Japan       doc_count=2
#   city        doc_count=1
#   tourism     doc_count=1
#   company     doc_count=1
# === 3. tags 集計（size=3、上位 3 件のみ）===
#   Japan       doc_count=4
#   city        doc_count=3
#   tourism     doc_count=2
