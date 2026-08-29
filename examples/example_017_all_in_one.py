# example_017_all_in_one.py
#
# JSONL import -> field rename -> add -> search -> view
#
# nlp4j-local-search の基本的な流れを1つのコードで確認する例。

import json
import tempfile
from pathlib import Path

from nlp4j_local_search import SearchEngine


# ------------------------------------------------------------
# 1. サンプル JSONL を作成
# ------------------------------------------------------------

documents = [
    {
        "id": "1",
        "text": "Kyoto is a historic city in Japan.",
        "category": "city",
    },
    {
        "id": "2",
        "text": "Nintendo is headquartered in Kyoto.",
        "category": "company",
    },
    {
        "id": "3",
        "text": "Tokyo is the capital city of Japan.",
        "category": "city",
    },
]


with tempfile.TemporaryDirectory() as tmpdir:

    jsonl_path = Path(tmpdir) / "sample.jsonl"

    with jsonl_path.open("w", encoding="utf-8") as f:
        for doc in documents:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    # --------------------------------------------------------
    # 2. JSONL を読み込み、フィールド名を変更してインデックスへロード
    #
    # text     -> body
    # category -> category_s
    # --------------------------------------------------------

    with SearchEngine("en", auto_analyze=False) as engine:

        result = (
            engine.data(jsonl_path)
                  .rename("text", "body")
                  .rename("category", "category_s")
                  .load()
        )

        print("=== Load ===")
        print(result)

        # ----------------------------------------------------
        # 3. Python から文書を1件追加
        # ----------------------------------------------------

        engine.add(
            "4",
            "Osaka is a major city in Japan.",
            fields={"category_s": "city"},
        )
        engine.commit()

        # ----------------------------------------------------
        # 4. 検索
        # ----------------------------------------------------

        print("\n=== Search: Kyoto ===")

        for r in engine.search("Kyoto", 10):
            print(f"[{r.id}] {r.body}")

        print("\n=== Search: category_s:city ===")

        for r in engine.search("category_s:city", 10):
            print(f"[{r.id}] {r.body}")

        # ----------------------------------------------------
        # 5. 分析
        #
        # category_s の値の分布を見る。
        # 検索キーワードを指定しなくてもデータの傾向を確認できる。
        # ----------------------------------------------------

        print("\n=== View: category_s ===")
        print(engine.view("category_s"))


