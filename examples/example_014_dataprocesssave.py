# example_014_dataprocesssave.py
#
# DataPipeline.write_jsonl() によるデータ加工・JSONL保存の例
#
# SearchEngine も JVM も不要です。
# nlp4j_local_search.data() を使うだけで JSONL の加工・保存が完結します。
#
# 操作:
#   - remove()      : 不要フィールドの削除
#   - rename()      : フィールド名の変更
#   - save_config() : パイプライン設定の JSON 保存（builder / 即時実行）
#   - write_jsonl() : 加工後 JSONL の保存（terminal operation）
#
# 入力ファイル (input.jsonl):
#   {"id": 1, "category": "city",    "text": "Kyoto is a historic city in Japan.",  "xxx": "aaa"}
#   {"id": 2, "category": "company", "text": "Nintendo is headquartered in Kyoto.", "xxx": "aaa"}
#   {"id": 3, "category": "city",    "text": "Tokyo is the capital city of Japan.", "xxx": "aaa"}
#
# 出力ファイル (output.jsonl):
#   {"id": 1, "category_s": "city",    "text_en": "Kyoto is a historic city in Japan."}
#   {"id": 2, "category_s": "company", "text_en": "Nintendo is headquartered in Kyoto."}
#   {"id": 3, "category_s": "city",    "text_en": "Tokyo is the capital city of Japan."}

import json
import os
import tempfile

# JVM は一切不要 — data() だけ import する
from nlp4j_local_search import data

# ---------------------------------------------------------------------------
# 1. 入力 JSONL ファイルを一時ディレクトリに作成
# ---------------------------------------------------------------------------
SAMPLE_DOCS = [
    {"id": 1, "category": "city",    "text": "Kyoto is a historic city in Japan.",  "xxx": "aaa"},
    {"id": 2, "category": "company", "text": "Nintendo is headquartered in Kyoto.", "xxx": "aaa"},
    {"id": 3, "category": "city",    "text": "Tokyo is the capital city of Japan.", "xxx": "aaa"},
]

with tempfile.TemporaryDirectory() as tmpdir:
    input_path  = os.path.join(tmpdir, "input.jsonl")
    output_path = os.path.join(tmpdir, "output.jsonl")
    config_path = os.path.join(tmpdir, "settings.json")

    with open(input_path, "w", encoding="utf-8") as f:
        for doc in SAMPLE_DOCS:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    # ---------------------------------------------------------------------------
    # 2. data() で JSONL 加工 → 保存（SearchEngine / JVM 不要）
    # ---------------------------------------------------------------------------
    result = (
        data(input_path)
            .remove("xxx")                      # "xxx" フィールドを削除
            .rename("category", "category_s")   # category → category_s
            .rename("text", "text_en")          # text → text_en
            .save_config(config_path)           # パイプライン設定を即時保存
            .write_jsonl(output_path)           # 加工後 JSONL を保存（terminal）
    )

    # ---------------------------------------------------------------------------
    # 3. WriteResult の表示
    # ---------------------------------------------------------------------------
    print("=== WriteResult ===")
    print(result)
    print(f"  count          : {result.count}")
    print(f"  path           : {result.path}")
    print(f"  elapsed_seconds: {result.elapsed_seconds:.4f}")

    # ---------------------------------------------------------------------------
    # 4. 加工後 JSONL の確認
    # ---------------------------------------------------------------------------
    print("\n=== 加工後 JSONL (output.jsonl) ===")
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
    # 6. iter_documents() で加工結果を Python から直接参照
    # ---------------------------------------------------------------------------
    print("=== iter_documents() による加工結果の確認 ===")
    pipeline = (
        data(input_path)
            .remove("xxx")
            .rename("category", "category_s")
            .rename("text", "text_en")
    )
    for doc in pipeline:
        print(" ", doc)

# expected output
#
# === WriteResult ===
# Wrote 3 documents to .../output.jsonl in 0.00 seconds.
#   count          : 3
#   path           : .../output.jsonl
#   elapsed_seconds: 0.0001
#
# === 加工後 JSONL (output.jsonl) ===
#   {"id": 1, "category_s": "city", "text_en": "Kyoto is a historic city in Japan."}
#   {"id": 2, "category_s": "company", "text_en": "Nintendo is headquartered in Kyoto."}
#   {"id": 3, "category_s": "city", "text_en": "Tokyo is the capital city of Japan."}
#
# === パイプライン設定 (settings.json) ===
# {
#   "version": 1,
#   "source": { "type": "jsonl", "path": "..." },
#   "transforms": [
#     { "type": "remove", "fields": ["xxx"] },
#     { "type": "rename", "source": "category", "target": "category_s" },
#     { "type": "rename", "source": "text", "target": "text_en" }
#   ]
# }
#
# === iter_documents() による加工結果の確認 ===
#   {"id": 1, "category_s": "city", "text_en": "Kyoto is a historic city in Japan."}
#   {"id": 2, "category_s": "company", "text_en": "Nintendo is headquartered in Kyoto."}
#   {"id": 3, "category_s": "city", "text_en": "Tokyo is the capital city of Japan."}
