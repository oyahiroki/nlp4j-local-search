# example_012_view.py
#
# engine.view() -- インデックスの中身を概観する inspection API
#
# view() は SearchEngine に格納されたデータを「ひと目で眺める」ための API です。
#
# 主な用途:
#   engine.view()                             全 aggregatable フィールドの上位値を一覧表示（count モード）
#   engine.view("category")                   単一フィールドの値を件数降順で表示（count モード）
#   engine.view("part", "maker:Nissan")       Lucene クエリで絞り込み + 単一フィールド（relativeRate モード）
#   engine.view(lucene_query="maker:Nissan")  全フィールド + Lucene 絞り込み（relativeRate モード）
#   result.sort_by("relative_rate")           relativeRate 降順で並べ替え（新オブジェクトを返す）
#   result.filter(min_relative_rate=1.5)      relativeRate しきい値でフィルター（新オブジェクトを返す）
#
# 戻り値は ViewResult オブジェクト。
# print() または Jupyter でセルに書くだけで整形表示されます。
# データとして使う場合は result.fields[n].buckets[n].key / .count / .relative_rate で参照できます。
#
# lucene_query に keyword フィールド（maker, category など）を指定する場合は
# relativeRateLucene() が呼ばれ、count / all_count / relative_rate が計算されます。
# (Example23_View.java 参照)

from nlp4j_local_search import SearchEngine, ViewResult

DOCUMENTS = [
    {"id": "1", "body": "Nissan reported a broken door mirror.",  "maker": "Nissan", "category": "body",       "part": "door mirror"},
    {"id": "2", "body": "Nissan reported a door mirror failure.", "maker": "Nissan", "category": "body",       "part": "door mirror"},
    {"id": "3", "body": "Nissan reported a battery problem.",     "maker": "Nissan", "category": "electrical", "part": "battery"},
    {"id": "4", "body": "Toyota reported a brake problem.",       "maker": "Toyota", "category": "brake",      "part": "brake"},
    {"id": "5", "body": "Toyota reported a battery problem.",     "maker": "Toyota", "category": "electrical", "part": "battery"},
    {"id": "6", "body": "Honda reported a brake problem.",        "maker": "Honda",  "category": "brake",      "part": "brake"},
]

with SearchEngine("en", auto_analyze=False) as engine:

    for doc in DOCUMENTS:
        engine.add_json(doc)

    engine.commit()

    # ------------------------------------------------------------------
    # 1. fields() -- インデックスの全フィールド名
    # ------------------------------------------------------------------
    print("=== 1. fields() ===")
    print(engine.fields())

    # ------------------------------------------------------------------
    # 2. aggregatable_fields() -- 集計可能なフィールド名
    # ------------------------------------------------------------------
    print()
    print("=== 2. aggregatable_fields() ===")
    print(engine.aggregatable_fields())

    # ------------------------------------------------------------------
    # 3. view() -- 全 aggregatable フィールドの概観（上位3件, count モード）
    # ------------------------------------------------------------------
    print()
    print("=== 3. view() ===")
    print(engine.view())

    # ------------------------------------------------------------------
    # 4. view("category") -- 単一フィールドを件数降順で表示（count モード）
    # ------------------------------------------------------------------
    print()
    print("=== 4. view('category') ===")
    print(engine.view("category"))

    # ------------------------------------------------------------------
    # 5. view("maker") -- 別フィールドを表示（count モード）
    # ------------------------------------------------------------------
    print()
    print("=== 5. view('maker') ===")
    print(engine.view("maker"))

    # ------------------------------------------------------------------
    # 6. view("part", "maker:Nissan")
    #    keyword フィールド Lucene クエリで絞り込んだ relativeRate モード
    #    Nissan ドキュメント(3件) 中の part 分布 vs. 全体(6件) での part 分布
    #    → door mirror: 2/3 vs 2/6 → relative_rate ≈ 2.0
    #    → battery:     1/3 vs 2/6 → relative_rate ≈ 1.0
    # ------------------------------------------------------------------
    print()
    print("=== 6. view('part', 'maker:Nissan') -- relativeRate mode ===")
    print(engine.view("part", "maker:Nissan"))

    # ------------------------------------------------------------------
    # 7. view(lucene_query="maker:Nissan") -- 全フィールド relativeRate モード
    # ------------------------------------------------------------------
    print()
    print("=== 7. view(lucene_query='maker:Nissan', size=5) ===")
    print(engine.view(lucene_query="maker:Nissan", size=5))

    # ------------------------------------------------------------------
    # 8. sort_by() -- buckets を並べ替えた新オブジェクトを返す
    #    sort_by() は ViewResult を mutate せず、新しい ViewResult を返す
    # ------------------------------------------------------------------
    print()
    print("=== 8. sort_by('count', descending=False) -- ascending count ===")
    result = engine.view("maker", size=10).sort_by("count", descending=False)
    print(result)

    print()
    print("=== 8b. sort_by('relative_rate') -- descending relative_rate ===")
    result = engine.view("part", "maker:Nissan").sort_by("relative_rate")
    print(result)

    # ------------------------------------------------------------------
    # 9. filter() -- しきい値で bucket を絞り込む（新オブジェクトを返す）
    #    filter() も ViewResult を mutate せず、新しい ViewResult を返す
    # ------------------------------------------------------------------
    print()
    print("=== 9. filter(min_relative_rate=1.5) ===")
    result = engine.view("part", "maker:Nissan").filter(min_relative_rate=1.5)
    print(result)
    # → door mirror (2.0x) のみ残る

    print()
    print("=== 9b. filter(min_count=2) ===")
    result = engine.view("maker", size=10).filter(min_count=2)
    print(result)
    # → count >= 2 の Nissan, Toyota のみ残る

    # ------------------------------------------------------------------
    # 10. チェーン操作 -- filter → sort_by
    # ------------------------------------------------------------------
    print()
    print("=== 10. filter + sort_by chain ===")
    result = (
        engine.view("part", "maker:Nissan")
        .filter(min_count=1)
        .sort_by("relative_rate")
    )
    print(result)

    # ------------------------------------------------------------------
    # 11. size と candidate_size の使い分け
    #
    #   candidate_size:
    #       relativeRate 計算対象として Java 側から取得する最大候補数。
    #       大きいほど統計的に精度が上がるが、計算コストも増える。
    #       デフォルト = 1000。
    #
    #   size:
    #       filter / sort 後に ViewResult へ表示する最大バケット数。
    #       デフォルト = 10 (単一フィールド) / 3 (全フィールド概観)。
    #
    #   典型的な使い方:
    #       candidate_size=1000 で幅広く候補を取り、
    #       size=10 で上位10件だけ表示する。
    # ------------------------------------------------------------------
    print()
    print("=== 11. size / candidate_size ===")
    result = engine.view(
        "part",
        "maker:Nissan",
        size=10,          # 表示する最大バケット数
        candidate_size=1000,  # Java 側 relativeRate 計算の最大候補数
    )
    print(result)

    # ------------------------------------------------------------------
    # 12. データとしての利用 -- result.fields / buckets でアクセス
    #     bucket.key は切り詰めなしの完全な値
    #     relativeRate モードでは bucket.relative_rate / bucket.all_count が利用可能
    # ------------------------------------------------------------------
    print()
    print("=== 12. ViewResult をデータとして使う ===")
    result = engine.view("part", "maker:Nissan")
    assert isinstance(result, ViewResult)

    vf = result.fields[0]
    print(f"  field: {vf.field}")
    print(f"  matched docs: {vf.count} / {vf.total_count}")
    for bucket in vf.buckets:
        print(
            f"    key={bucket.key!r:16s} "
            f"count={bucket.count}  "
            f"all_count={bucket.all_count}  "
            f"relative_rate={bucket.relative_rate:.2f}x"
        )

# Expected output (abbreviated):
#
# === 3. view() ===
# View: aggregatable fields
# Format: field | value (document count)
#
# maker    | Nissan (3), Toyota (2), Honda (1)
# category | brake (2), body (2), electrical (2)
# part     | brake (2), door mirror (2), battery (2)
#
# === 6. view('part', 'maker:Nissan') -- relativeRate モード ===
# View: part
# Lucene query: maker:Nissan
# Matched documents: 3 / 6
# Values are ordered by relative rate.
#
# Rank  Value                Count  All Count  Relative Rate
# ----  -------------------- --------  ----------  --------------
#    1  door mirror              2          2          2.00x
#    2  battery                  1          2          1.00x
#
# === 9. filter(min_relative_rate=1.5) ===
# View: part
# Lucene query: maker:Nissan
# Matched documents: 3 / 6
# Values are ordered by relative rate.
#
# Rank  Value                Count  All Count  Relative Rate
# ----  -------------------- --------  ----------  --------------
#    1  door mirror              2          2          2.00x
#
# === 12. ViewResult をデータとして使う ===
#   field: part
#   matched docs: 3 / 6
#     key='door mirror'    count=2  all_count=2  relative_rate=2.00x
#     key='battery'        count=1  all_count=2  relative_rate=1.00x
