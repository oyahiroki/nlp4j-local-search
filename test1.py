from nlp4j_local_search import SearchEngine

with SearchEngine(
    "ja",
    auto_analyze=True,
) as engine:

    engine.add_json({
        "id": "222",
        "text_ja": "日本の漫画家では、日本における漫画家について解説する。",
        "category_s": ["日本の漫画家"],
    })

    engine.commit()

    print(engine.count())
