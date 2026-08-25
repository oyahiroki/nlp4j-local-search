# example_013_dataprocess.py
#
# DataPipeline によるデータ加工・保存・ロードの例
#
# JSONL ファイルを読み込み、
#   - remove()    : 不要フィールドの削除
#   - rename()    : フィールド名の変更
#   - save_as()   : 加工後 JSONL の保存
#   - save_config(): パイプライン設定の JSON 保存
#   - load()      : SearchEngine へのインデックス投入
# を fluent API で記述します。
#
# 入力ファイル (test.jsonl):
#   {"id": 1, "category": "city",    "text": "Kyoto is a historic city in Japan.",  "xxx": "aaa"}
#   {"id": 2, "category": "company", "text": "Nintendo is headquartered in Kyoto.", "xxx": "aaa"}
#   {"id": 3, "category": "city",    "text": "Tokyo is the capital city of Japan.", "xxx": "aaa"}
#
# 出力ファイル (test_out.jsonl):
#   {"id": 1, "category_s": "city",    "body": "Kyoto is a historic city in Japan."}
#   {"id": 2, "category_s": "company", "body": "Nintendo is headquartered in Kyoto."}
#   {"id": 3, "category_s": "city",    "body": "Tokyo is the capital city of Japan."}

import json
import os
import tempfile

from nlp4j_local_search import SearchEngine

# ---------------------------------------------------------------------------
# 1. 入力 JSONL ファイルを一時ディレクトリに作成
# ---------------------------------------------------------------------------
SAMPLE_DOCS = [
    {"id": 1, "category": "city",    "text": "Kyoto is a historic city in Japan.",  "xxx": "aaa"},
    {"id": 2, "category": "company", "text": "Nintendo is headquartered in Kyoto.", "xxx": "aaa"},
    {"id": 3, "category": "city",    "text": "Tokyo is the capital city of Japan.", "xxx": "aaa"},
]

with tempfile.TemporaryDirectory() as tmpdir:
    input_path  = os.path.join(tmpdir, "test.jsonl")
    output_path = os.path.join(tmpdir, "test_out.jsonl")
    config_path = os.path.join(tmpdir, "settings.json")

    with open(input_path, "w", encoding="utf-8") as f:
        for doc in SAMPLE_DOCS:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    # ---------------------------------------------------------------------------
    # 2. SearchEngine + DataPipeline でデータ加工・保存・インデックス投入
    # ---------------------------------------------------------------------------
    with SearchEngine("en", auto_analyze=False) as engine:

        result = (
            engine.data(input_path)
                  .remove("xxx")                      # "xxx" フィールドを削除
                  .rename("category", "category_s")   # category → category_s
                  .rename("text", "body")             # text → body（検索対象フィールド）
                  .save_as(output_path)               # 加工後 JSONL を保存
                  .save_config(config_path)           # パイプライン設定を JSON 保存
                  .load()                             # SearchEngine へロード
        )

        # ---------------------------------------------------------------------------
        # 3. LoadResult の表示
        # ---------------------------------------------------------------------------
        print("=== LoadResult ===")
        print(result)
        print(f"  read_count   : {result.read_count}")
        print(f"  loaded_count : {result.loaded_count}")
        print(f"  written_count: {result.written_count}")
        print(f"  output_path  : {result.output_path}")

        # ---------------------------------------------------------------------------
        # 4. 加工後 JSONL の確認
        # ---------------------------------------------------------------------------
        print("\n=== 加工後 JSONL (test_out.jsonl) ===")
        with open(output_path, encoding="utf-8") as f:
            for line in f:
                print(" ", line.rstrip())

        # ---------------------------------------------------------------------------
        # 5. 保存された設定 JSON の確認
        # ---------------------------------------------------------------------------
        print("\n=== パイプライン設定 (settings.json) ===")
        with open(config_path, encoding="utf-8") as f:
            print(f.read())

        # ---------------------------------------------------------------------------
        # 6. 検索
        # ---------------------------------------------------------------------------
        print("=== キーワード検索: 'city' ===")
        for r in engine.search("city", 10):
            print(f"  [{r.id}] {r.body}")

        print("\n=== フィールド絞り込み: category_s:city ===")
        for r in engine.search("category_s:city", 10):
            print(f"  [{r.id}] {r.body}")

        print("\n=== フィールド絞り込み: category_s:company ===")
        for r in engine.search("category_s:company", 10):
            print(f"  [{r.id}] {r.body}")

# expected output
#
# === LoadResult ===
# Loaded 3 documents in 0.00 seconds.
#   read_count   : 3
#   loaded_count : 3
#   written_count: 3
#   output_path  : .../test_out.jsonl
#
# === 加工後 JSONL (test_out.jsonl) ===
#   {"id": 1, "category_s": "city", "body": "Kyoto is a historic city in Japan."}
#   {"id": 2, "category_s": "company", "body": "Nintendo is headquartered in Kyoto."}
#   {"id": 3, "category_s": "city", "body": "Tokyo is the capital city of Japan."}
#
# === パイプライン設定 (settings.json) ===
# {
#   "version": 1,
#   "source": { "type": "jsonl", "path": "..." },
#   "transforms": [
#     { "type": "remove", "fields": ["xxx"] },
#     { "type": "rename", "source": "category", "target": "category_s" },
#     { "type": "rename", "source": "text", "target": "body" }
#   ],
#   "output": { "type": "jsonl", "path": "..." }
# }
#
# === キーワード検索: 'city' ===
#   [1] Kyoto is a historic city in Japan.
#   [3] Tokyo is the capital city of Japan.
#
# === フィールド絞り込み: category_s:city ===
#   [1] Kyoto is a historic city in Japan.
#   [3] Tokyo is the capital city of Japan.
#
# === フィールド絞り込み: category_s:company ===
#   [2] Nintendo is headquartered in Kyoto.
