# example_009_view_ja.py
#
# relative_rate() による日本語テキストマイニング
#
# relative_rate() はある観点 (query_field / query_value) で絞り込んだ文書集合において、
# 指定フィールドの値が全体と比べてどれだけ特徴的か (relative_rate) を返す。
#
#   relative_rate = (対象文書内の出現率) / (全文書内の出現率)
#
# 値が大きいほど、その語がその観点の文書集合に特有であることを示す。
# 計算は Java の LocalAnalytics が行うため、Python 側では結果を受け取るだけ。

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
    # 1. ニッサン文書に特徴的な名詞
    # ------------------------------------------------------------------
    print("=== ニッサン に特徴的な word.noun ===")
    result = engine.relative_rate(
        query_field="word.noun",
        query_value="ニッサン",
        field="word.noun",
        size=100,
    )
    print(f"  対象文書数: {result.count}  全文書数: {result.total_count}")
    for bucket in result.buckets:
        print(
            f"  {bucket.key:12s}"
            f"  count={bucket.count}"
            f"  all_count={bucket.all_count}"
            f"  relative_rate={bucket.relative_rate:.4f}"
        )

    # ------------------------------------------------------------------
    # 2. ニッサン文書に特徴的な動詞
    # ------------------------------------------------------------------
    print()
    print("=== ニッサン に特徴的な word.verb ===")
    result = engine.relative_rate(
        query_field="word.noun",
        query_value="ニッサン",
        field="word.verb",
        size=100,
    )
    for bucket in result.buckets:
        print(
            f"  {bucket.key:12s}"
            f"  count={bucket.count}"
            f"  all_count={bucket.all_count}"
            f"  relative_rate={bucket.relative_rate:.4f}"
        )

    # ------------------------------------------------------------------
    # 3. トヨタ文書に特徴的な名詞
    # ------------------------------------------------------------------
    print()
    print("=== トヨタ に特徴的な word.noun ===")
    result = engine.relative_rate(
        query_field="word.noun",
        query_value="トヨタ",
        field="word.noun",
        size=100,
    )
    for bucket in result.buckets:
        print(
            f"  {bucket.key:12s}"
            f"  count={bucket.count}"
            f"  all_count={bucket.all_count}"
            f"  relative_rate={bucket.relative_rate:.4f}"
        )

# Expected output (抜粋):
# === ニッサン に特徴的な word.noun ===
#   対象文書数: 2  全文書数: 5
#   ニッサン      count=2  all_count=2  relative_rate=2.5000
#   破損          count=1  all_count=1  relative_rate=2.5000
#   ドアミラー    count=2  all_count=3  relative_rate=1.6667
#   ミラー        count=2  all_count=3  relative_rate=1.6667
#   ドア          count=2  all_count=4  relative_rate=1.2500
# === ニッサン に特徴的な word.verb ===
#   動く          count=1  all_count=1  relative_rate=2.5000
# === トヨタ に特徴的な word.noun ===
#   トヨタ        count=3  all_count=3  relative_rate=1.6667
#   水            count=1  all_count=1  relative_rate=1.6667
#   ブレーキ      count=1  all_count=1  relative_rate=1.6667
