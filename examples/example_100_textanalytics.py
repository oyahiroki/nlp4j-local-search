
# example_aggregation_keywords_10docs.py
#
# 10件の日本語文書を登録し、以下を実行する例
#
# 1. 全10文書を対象とした keywords aggregation
# 2. query="京都" で絞り込んだ keywords aggregation

import json

from nlp4j_local_search import SearchEngine


documents = [
    {
        "id": "id001",
        "text": "京都は日本の歴史ある都市です",
        "keywords": ["京都", "日本", "歴史", "ある", "都市"],
    },
    {
        "id": "id002",
        "text": "京都の寺院を観光します",
        "keywords": ["京都", "寺院", "観光する"],
    },
    {
        "id": "id003",
        "text": "東京は日本の大きな都市です",
        "keywords": ["東京", "日本", "大きい", "都市"],
    },
    {
        "id": "id004",
        "text": "私は学校で数学を学びます",
        "keywords": ["私", "学校", "数学", "学ぶ"],
    },
    {
        "id": "id005",
        "text": "学校の生徒は図書館で本を読みます",
        "keywords": ["学校", "生徒", "図書館", "本", "読む"],
    },
    {
        "id": "id006",
        "text": "明日は良い天気です",
        "keywords": ["明日", "良い", "天気"],
    },
    {
        "id": "id007",
        "text": "今日は強い雨が降ります",
        "keywords": ["今日", "強い", "雨", "降る"],
    },
    {
        "id": "id008",
        "text": "犬が公園を元気に走ります",
        "keywords": ["犬", "公園", "元気", "走る"],
    },
    {
        "id": "id009",
        "text": "猫は暖かい部屋で眠ります",
        "keywords": ["猫", "暖かい", "部屋", "眠る"],
    },
    {
        "id": "id010",
        "text": "京都の大学で日本文化を勉強します",
        "keywords": ["京都", "大学", "日本", "文化", "勉強する"],
    },
]


def print_aggregation(response: dict, field_name: str) -> None:
    """Aggregationのバケットを表示する。"""

    buckets = response["aggregations"][field_name]["buckets"]

    for bucket in buckets:
        print(
            f"  {bucket['key']:10s} "
            f"doc_count={bucket['doc_count']}"
        )


with SearchEngine("ja") as engine:

    # ------------------------------------------------------------
    # 登録する文書を表示
    # ------------------------------------------------------------
    print("=== 登録する文書 ===")

    for document in documents:
        print(
            json.dumps(
                document,
                ensure_ascii=False,
            )
        )

    # ------------------------------------------------------------
    # 文書登録
    #
    # keywordsはJSON配列なので、配列内の各要素が
    # MultiValued keyword fieldとして登録される。
    # ------------------------------------------------------------
    for document in documents:
        engine.add_json(document)

    engine.commit()

    # ------------------------------------------------------------
    # 1. 全10文書を対象としたkeywords集計
    # ------------------------------------------------------------
    print()
    print("=== 1. keywords 全件集計 ===")

    response = engine.aggregate(
        "keywords",
        size=100,
    )

    print_aggregation(response, "keywords")

    # ------------------------------------------------------------
    # 2. 「京都」で文書を絞り込んだkeywords集計
    #
    # 対象となる文書:
    #   id001 京都は日本の歴史ある都市です
    #   id002 京都の寺院を観光します
    #   id010 京都の大学で日本文化を勉強します
    # ------------------------------------------------------------
    query = "京都"

    print()
    print(f'=== 2. keywords 集計（query="{query}"）===')

    response = engine.aggregate(
        "keywords",
        size=100,
        query=query,
    )

    print_aggregation(response, "keywords")