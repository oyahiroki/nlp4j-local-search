# example_008_auto_analyze_ja.py
#
# 日本語テキストの自動形態素解析 (auto_analyze)
#
# SearchEngine("ja") はデフォルトで auto_analyze=True。
# 自然文を add() するだけで Java 側が形態素解析し、
#   word.noun  (名詞)
#   word.verb  (動詞の基本形)
# などのフィールドを自動生成する。
# これを aggregate() で集計できる。

from nlp4j_local_search import SearchEngine

DOCUMENTS = [
    ("1", "ニッサン ドアミラーが破損"),
    ("2", "ニッサン ドアミラーが動かない"),
    ("3", "トヨタ ドアミラーが外れた"),
    ("4", "トヨタ ブレーキの効きが悪い"),
    ("5", "トヨタ ドアから水が入った"),
]

with SearchEngine("ja") as engine:

    for doc_id, body in DOCUMENTS:
        engine.add(doc_id, body)

    engine.commit()

    # ------------------------------------------------------------------
    # 1. 全文書の名詞集計
    # ------------------------------------------------------------------
    print("=== 全文書: word.noun 集計 ===")
    result = engine.aggregate("word.noun", size=50)
    for bucket in result["aggregations"]["word.noun"]["buckets"]:
        print(f"  {bucket['key']:12s}  {bucket['doc_count']} 件")

    # ------------------------------------------------------------------
    # 2. 全文書の動詞集計
    # ------------------------------------------------------------------
    print()
    print("=== 全文書: word.verb 集計 ===")
    result = engine.aggregate("word.verb", size=50)
    for bucket in result["aggregations"]["word.verb"]["buckets"]:
        print(f"  {bucket['key']:12s}  {bucket['doc_count']} 件")

    # ------------------------------------------------------------------
    # 3. キーワード検索 ("ドアミラー") と word.noun 集計の組み合わせ
    # ------------------------------------------------------------------
    print()
    print('=== "ドアミラー" を含む文書の word.noun 集計 ===')
    result = engine.aggregate("word.noun", size=50, query="ドアミラー")
    for bucket in result["aggregations"]["word.noun"]["buckets"]:
        print(f"  {bucket['key']:12s}  {bucket['doc_count']} 件")

# Expected output (抜粋):
# === 全文書: word.noun 集計 ===
#   ドア          4 件
#   トヨタ        3 件
#   ドアミラー    3 件
#   ミラー        3 件
#   ニッサン      2 件
#   水            1 件
#   ブレーキ      1 件
#   破損          1 件
# === 全文書: word.verb 集計 ===
#   動く          1 件
#   外れる        1 件
#   入る          1 件
#   効く          1 件
# === "ドアミラー" を含む文書の word.noun 集計 ===
#   ドア          4 件
#   ドアミラー    3 件
#   ミラー        3 件
#   トヨタ        2 件
#   ニッサン      2 件
#   水            1 件
#   破損          1 件
