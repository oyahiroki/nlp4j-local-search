from nlp4j_local_search import SearchEngine
from pprint import pprint

documents = [
    {"id": "1", "body": "Kyoto is a historic city.",
     "tags": ["city", "tourism", "Japan"]},
    {"id": "2", "body": "Nintendo is headquartered in Kyoto.",
     "tags": ["company", "Japan"]},
    {"id": "3", "body": "Tokyo is the capital city of Japan.",
     "tags": ["city", "capital", "Japan"]},
]

with SearchEngine("en") as engine:

    for doc in documents:
        engine.add_json(doc)

    engine.commit()

    response = engine.search_response_json({
        "size": 10,
        "query": {
            "bool": {
                "filter": [
                    {"term": {"tags": "Japan"}},
                    {"term": {"tags": "city"}},
                ]
            }
        },
    })

    pprint(response)
