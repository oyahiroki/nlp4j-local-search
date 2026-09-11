from nlp4j_local_search import SearchEngine

documents = [
    {"id": "1", "body": "東京都は日本の都道府県のひとつです"},
    {"id": "2", "body": "京都は日本の都市です。"},
    {"id": "3", "body": "京都市には任天堂の本社があります"},
    {"id": "4", "body": "京都府は広いです"},
]

print("=== データ ===")
for doc in documents:
    print(doc)

print()

print("=== テキスト検索の例 (京都) ===")
with SearchEngine("ja") as engine:

    # データを登録
    for doc in documents:
        engine.add_json(doc)

    engine.commit()

    # 検索
    for r in engine.search("京都", 10):
        print(r.id, r.body, r.score)


# expected output
#
# === データ ===
# {'id': '1', 'body': '東京都は日本の都道府県のひとつです'}
# {'id': '2', 'body': '京都は日本の都市です。'}
# {'id': '3', 'body': '京都市には任天堂の本社があります'}
# {'id': '4', 'body': '京都府は広いです'}
#
# === テキスト検索の例 ===
# 2 京都は日本の都市です。 0.18059490621089935
# 4 京都府は広いです 0.18059490621089935
# 3 京都市には任天堂の本社があります 0.16212496161460876