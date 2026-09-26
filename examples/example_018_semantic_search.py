# セマンティック検索（テキスト自動 Embedding）の使用例
#
# 必要なパッケージ:
#   pip install nlp4j-local-search
#   pip install nlp4j-local-search-embedding
#
# nlp4j-local-search-embedding は初回実行時に
#   intfloat/multilingual-e5-large（約2.2GB）を
#   Hugging Face からダウンロードします。

from nlp4j_local_search import SearchEngine

documents = [
    {"id": "1", "body": "京都は日本の古都です"},
    {"id": "2", "body": "東京は日本最大の都市です"},
    {"id": "3", "body": "奈良には歴史的な寺院があります"},
    {"id": "4", "body": "大阪は食文化で有名な都市です"},
    {"id": "5", "body": "北海道は広大な自然が広がっています"},
]

print("=== データ ===")
for doc in documents:
    print(doc)

print()

# embedding=True を指定すると以下が自動で行われる:
#   - デフォルト Embedding モデル (intfloat/multilingual-e5-large, 1024次元) が読み込まれる
#   - add(id, text) 呼び出し時にテキストをベクトル化し、テキストとベクトルを同時にインデックスへ登録する
#   - search_semantic(query) でテキストをベクトル化してベクトル検索が実行できる
#   - search(query) によるキーワード検索も引き続き利用できる

print("Embedding モデルを読み込んでいます...")

with SearchEngine("ja", embedding=True) as engine:

    print("ドキュメントを登録しています（自動ベクトル化）...")
    for doc in documents:
        engine.add(doc["id"], doc["body"])

    engine.commit()
    print(f"登録完了: {engine.count()} 件\n")

    # --- キーワード検索 (Lucene Query Syntax) ---
    print("=== キーワード検索: '京都' ===")
    for r in engine.search("京都", limit=5):
        print(f"  [{r.id}] {r.body}  (score: {r.score:.4f})")

    print()

    # --- セマンティック検索 ---
    # クエリテキストを自動的にベクトル化して、意味的に近いドキュメントを返す
    queries = [
        "日本の古い都",
        "大きな街",
        "お寺や神社",
    ]

    for query in queries:
        print(f"=== セマンティック検索: '{query}' ===")
        for r in engine.search_semantic(query, limit=3):
            print(f"  [{r.id}] {r.body}  (score: {r.score:.4f})")
        print()

    # --- filter_query との組み合わせ ---
    # Lucene クエリで絞り込みながらセマンティック検索を行う例
    print("=== セマンティック検索 + filter_query: '都市' (id:1 OR id:2 のみ対象) ===")
    for r in engine.search_semantic(
        "都市",
        limit=5,
        filter_query="id:1 OR id:2",
    ):
        print(f"  [{r.id}] {r.body}  (score: {r.score:.4f})")

print("\n完了！")


# expected output (score は環境により異なる):
#
# === データ ===
# {'id': '1', 'body': '京都は日本の古都です'}
# ...
#
# === キーワード検索: '京都' ===
#   [1] 京都は日本の古都です  (score: 0.xxxx)
#
# === セマンティック検索: '日本の古い都' ===
#   [1] 京都は日本の古都です  (score: 0.xxxx)
#   [3] 奈良には歴史的な寺院があります  (score: 0.xxxx)
#   [2] 東京は日本最大の都市です  (score: 0.xxxx)
#
# === セマンティック検索: '大きな街' ===
#   [2] 東京は日本最大の都市です  (score: 0.xxxx)
#   ...
#
# === セマンティック検索 + filter_query: '都市' (id:1 OR id:2 のみ対象) ===
#   [2] 東京は日本最大の都市です  (score: 0.xxxx)
#   [1] 京都は日本の古都です  (score: 0.xxxx)
