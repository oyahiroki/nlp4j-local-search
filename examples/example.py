from nlp4j_local_search import SearchEngine

with SearchEngine("ja") as engine:
    engine.add("1", "東京都は日本の都道府県のひとつです")
    engine.add("2", "京都は日本の都市です。")
    engine.add("3", "京都市には任天堂の本社があります")
    engine.add_json({"id": "4", "body": "京都府は広いです"})

    engine.commit()

    for r in engine.search("京都", limit=10):
        print(r.id, r.body, r.score)