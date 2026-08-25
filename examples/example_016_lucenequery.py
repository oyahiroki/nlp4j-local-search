# example_016_lucenequery.py
#
# Lucene Query 構文を使った検索の例
#
# engine.search(query, limit) を使って
# Lucene のクエリ構文をそのまま利用できます。
#
# テキストフィールドの内部名:
#   "en" エンジン → text_en
#   "ja" エンジン → text_ja
#
# 対応するクエリ例:
#   text_en:Kyoto                        フィールド指定キーワード
#   text_en:Kyoto AND text_en:historic   AND 条件
#   text_en:Kyoto OR  text_en:Tokyo      OR 条件
#   category:city                        keyword フィールドの完全一致
#   category:city AND text_en:Kyoto      keyword + full-text の複合条件
#   text_en:Kyo*                         ワイルドカード
#   text_en:"historic city"              フレーズ検索
#
# データセット:
#   id  body                                           category  country
#   1   Kyoto is a historic city in Japan.             city      Japan
#   2   Tokyo is the capital city of Japan.            city      Japan
#   3   Paris is the capital city of France.           city      France
#   4   Nintendo is headquartered in Kyoto, Japan.     company   Japan
#   5   Sony is a Japanese multinational company.      company   Japan
#   6   Microsoft is headquartered in Redmond, USA.    company   USA

from nlp4j_local_search import SearchEngine

DOCS = [
    {"id": "1", "body": "Kyoto is a historic city in Japan.",
     "category": "city",    "country": "Japan"},
    {"id": "2", "body": "Tokyo is the capital city of Japan.",
     "category": "city",    "country": "Japan"},
    {"id": "3", "body": "Paris is the capital city of France.",
     "category": "city",    "country": "France"},
    {"id": "4", "body": "Nintendo is headquartered in Kyoto, Japan.",
     "category": "company", "country": "Japan"},
    {"id": "5", "body": "Sony is a Japanese multinational company.",
     "category": "company", "country": "Japan"},
    {"id": "6", "body": "Microsoft is headquartered in Redmond, USA.",
     "category": "company", "country": "USA"},
]


def show(label, results):
    total = len(results)
    print(f"\n=== {label} (hits: {total}) ===")
    for r in results:
        print(f"  [{r.id}] {r.body}")


with SearchEngine("en", auto_analyze=False) as engine:

    # ----------------------------------------------------------------
    # データ登録
    # ----------------------------------------------------------------
    for doc in DOCS:
        engine.add_json(doc)
    engine.commit()

    # ----------------------------------------------------------------
    # 1. フィールド指定キーワード検索: text_en:Kyoto
    # ----------------------------------------------------------------
    show("text_en:Kyoto", engine.search("text_en:Kyoto", 10))

    # ----------------------------------------------------------------
    # 2. AND 条件: text_en:Kyoto AND text_en:historic
    # ----------------------------------------------------------------
    show("text_en:Kyoto AND text_en:historic",
         engine.search("text_en:Kyoto AND text_en:historic", 10))

    # ----------------------------------------------------------------
    # 3. OR 条件: text_en:Kyoto OR text_en:Tokyo
    # ----------------------------------------------------------------
    show("text_en:Kyoto OR text_en:Tokyo",
         engine.search("text_en:Kyoto OR text_en:Tokyo", 10))

    # ----------------------------------------------------------------
    # 4. keyword フィールドの完全一致: category:city
    # ----------------------------------------------------------------
    show("category:city", engine.search("category:city", 10))

    # ----------------------------------------------------------------
    # 5. keyword + full-text 複合条件: category:company AND text_en:Kyoto
    # ----------------------------------------------------------------
    show("category:company AND text_en:Kyoto",
         engine.search("category:company AND text_en:Kyoto", 10))

    # ----------------------------------------------------------------
    # 6. keyword 複合条件: category:city AND country:Japan
    # ----------------------------------------------------------------
    show("category:city AND country:Japan",
         engine.search("category:city AND country:Japan", 10))

    # ----------------------------------------------------------------
    # 7. ワイルドカード: text_en:Kyo*
    # ----------------------------------------------------------------
    show("text_en:Kyo*", engine.search("text_en:Kyo*", 10))

    # ----------------------------------------------------------------
    # 8. フレーズ検索: text_en:"historic city"
    # ----------------------------------------------------------------
    show('text_en:"historic city"', engine.search('text_en:"historic city"', 10))

    # ----------------------------------------------------------------
    # 9. NOT 条件: category:city AND NOT country:Japan
    # ----------------------------------------------------------------
    show("category:city AND NOT country:Japan",
         engine.search("category:city AND NOT country:Japan", 10))

# expected output
#
# === text_en:Kyoto (hits: 2) ===
#   [1] Kyoto is a historic city in Japan.
#   [4] Nintendo is headquartered in Kyoto, Japan.
#
# === text_en:Kyoto AND text_en:historic (hits: 1) ===
#   [1] Kyoto is a historic city in Japan.
#
# === text_en:Kyoto OR text_en:Tokyo (hits: 3) ===
#   [1] Kyoto is a historic city in Japan.
#   [4] Nintendo is headquartered in Kyoto, Japan.
#   [2] Tokyo is the capital city of Japan.
#
# === category:city (hits: 3) ===
#   [1] Kyoto is a historic city in Japan.
#   [2] Tokyo is the capital city of Japan.
#   [3] Paris is the capital city of France.
#
# === category:company AND text_en:Kyoto (hits: 1) ===
#   [4] Nintendo is headquartered in Kyoto, Japan.
#
# === category:city AND country:Japan (hits: 2) ===
#   [1] Kyoto is a historic city in Japan.
#   [2] Tokyo is the capital city of Japan.
#
# === text_en:Kyo* (hits: 2) ===
#   [1] Kyoto is a historic city in Japan.
#   [4] Nintendo is headquartered in Kyoto, Japan.
#
# === text_en:"historic city" (hits: 1) ===
#   [1] Kyoto is a historic city in Japan.
#
# === category:city AND NOT country:Japan (hits: 1) ===
#   [3] Paris is the capital city of France.
