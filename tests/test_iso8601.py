from nlp4j_local_search import SearchEngine

def test_date_field_iso8601():
    engine = SearchEngine("en", auto_analyze=False)

    engine.add_json({
        "id": "1",
        "body": "a",
        "date": "2024-03-01",
    })
    engine.add_json({
        "id": "2",
        "body": "b",
        "date": "2026-09-14",
    })
    engine.commit()

    buckets = engine.date_histogram("date", "year")

    values = {
        bucket.key: bucket.doc_count
        for bucket in buckets
    }

    assert values["2024"] == 1
    assert values["2025"] == 0
    assert values["2026"] == 1

    engine.close()