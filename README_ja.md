![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-Apache--2.0-green)

https://github.com/oyahiroki/nlp4j-local-search

# nlp4j-local-search

[English](README.md) | 日本語

**Elasticsearch、OpenSearch、Solr、Docker を使わずに、Apache Lucene を Python から利用できます。**

`nlp4j-local-search` は Python 向けの軽量オンメモリ全文検索ライブラリです。

サーバーや Docker の構築なしに、Apache Lucene ベースの検索機能を Python から直接利用できます。

このライブラリは以下のような用途に適しています。

- 自然言語処理の実験
- RAG のプロトタイピング
- ローカル全文検索
- Jupyter Notebook・Google Colab での実験
- 小規模検索アプリケーション
- 一時的な検索インデックスが必要なテストコード

内部実装は Java と Apache Lucene を利用していますが、Python 利用者が Java を意識する必要はありません。

---

## なぜこのライブラリ？

Elasticsearch・OpenSearch・Apache Solr はいずれも強力な検索エンジンであり、Apache Lucene を基盤としています。

しかし、小規模な実験やローカルプロトタイプ、Notebook での作業では、サーバーを立ち上げるのは重すぎることがあります。

`nlp4j-local-search` を使えば、Python プロセスの中に直接 Lucene ベースの検索インデックスを作成できます。

```python
from nlp4j_local_search import SearchEngine

with SearchEngine("ja") as engine:
    engine.add("1", "東京都は日本の都道府県のひとつです")
    engine.add("2", "京都は日本の都市です")
    engine.add("3", "京都市には任天堂の本社があります")

    engine.commit()

    for r in engine.search("京都"):
        print(r.id, r.body, r.score)
```

サーバー不要。Docker 不要。外部の検索エンジンプロセス不要。

---

## 特徴

- Python ファーストな API
- Apache Lucene ベースの全文検索
- オンメモリローカル検索
- Elasticsearch 不要
- OpenSearch 不要
- Solr 不要
- Docker 不要
- 日本語全文検索対応
- 英語全文検索対応
- JSON ドキュメント入力対応
- **フィールド絞り込み** — キーワード完全一致（AND 条件）でのフィールドフィルター
- **ベクトル検索（KNN）** — float ベクトルによる近傍検索
- **フィールド付きベクトル検索** — フィールド絞り込みスコープ内での KNN 検索
- **MultiValued フィールド** — JSON 配列フィールドを登録し、各要素を独立したキーワード値としてインデックス
- **Aggregation** — `aggregate()` / `aggregate_json()` による terms aggregation
- **OpenSearch Query DSL** — `search_json()` / `search_response_json()` による複雑なクエリ
- **`view()` inspection API** — インデックスの中身をひと目で把握；count モードと relativeRate モード、`sort_by()` / `filter()` チェーン操作対応
- NLP・RAG 実験に最適

---

## インストール

```bash
pip install nlp4j-local-search
```

### 開発版のインストール

```bash
git clone https://github.com/oyahiroki/nlp4j-local-search.git
cd nlp4j-local-search
pip install -e .
```

---

## 動作要件

- Python 3.8 以上
- Java ランタイム環境（JRE 8 以上）
- jpype1

---

## クイックスタート

```python
from nlp4j_local_search import SearchEngine

engine = SearchEngine("ja")

engine.add("1", "東京都は日本の都道府県のひとつです")
engine.add("2", "京都は日本の都市です")
engine.add("3", "京都市には任天堂の本社があります")

engine.commit()

results = engine.search("京都")

for r in results:
    print(r.id, r.body, r.score)

engine.close()
```

コンテキストマネージャ（`with` 文）の使用を推奨します。

```python
from nlp4j_local_search import SearchEngine

with SearchEngine("ja") as engine:
    engine.add("1", "東京都は日本の都道府県のひとつです")
    engine.add("2", "京都は日本の都市です。")
    engine.add("3", "京都市には任天堂の本社があります")
    engine.add_json({"id": "4", "body": "京都府は広いです"})

    engine.commit()

    for r in engine.search("京都", limit=10):
        print(r.id, r.body, r.score)
```

実行結果の例：

```text
2 京都は日本の都市です。 0.18059490621089935
4 京都府は広いです 0.18059490621089935
3 京都市には任天堂の本社があります 0.16212496161460876
```

---

## ドキュメントの登録

ID と本文テキストを指定してドキュメントを追加します。

```python
engine.add("1", "京都は日本の歴史的な都市です。")
```

フィルター検索用の追加フィールドを付けることもできます。

```python
engine.add("1", "京都は日本の歴史的な都市です。",
           fields={"category": "city", "country": "Japan"})
engine.add("2", "任天堂の本社は京都にあります。",
           fields={"category": "company", "country": "Japan"})
```

`fields` の値は文字列のみ使用できます。フィールドはキーワードフィールド（アナライザーを通さない完全一致）として保存されます。
`id`・`body`・`vector` は予約済みフィールド名のため使用できません。

---

## JSON ドキュメントの登録

Python の辞書として追加できます。

```python
engine.add_json({
    "id": "1",
    "body": "京都は日本の歴史的な都市です。",
    "category": "city",
    "country": "Japan"
})
```

JSON 文字列としても追加できます。

```python
engine.add_json("""
{
  "id": "2",
  "body": "大阪は関西の大都市です。",
  "category": "city",
  "country": "Japan"
}
""")
```

`id`・`body` 以外の JSON キーは自動的にキーワードフィールドとして登録されます。

---

## 検索

```python
results = engine.search("京都")
```

件数を指定する場合：

```python
results = engine.search("京都", limit=10)
```

各結果は以下の属性を持ちます。

```python
r.id     # ドキュメント ID
r.body   # 本文テキスト
r.score  # 検索スコア
```

---

## フィールド絞り込み

`filters` キーワード引数で、フィールド値による絞り込みができます。
複数指定した場合はすべて AND 条件になります。

```python
# 単一フィールドで絞り込み
results = engine.search("京都", limit=10, filters={"category": "city"})

# 複数フィールドで絞り込み（AND条件）
results = engine.search("京都", limit=10,
                        filters={"category": "city", "country": "Japan"})

# クエリなし（match_all）+ フィールド絞り込み
results = engine.search("", limit=10, filters={"country": "Japan"})
```

フィールド値は全文検索ではなく、キーワード完全一致（term クエリ）で評価されます。
そのため、スコアは本文のキーワード一致度のみで決まります。

### フル例

```python
from nlp4j_local_search import SearchEngine

with SearchEngine("ja") as engine:
    engine.add_json({"id": "1", "body": "京都は日本の歴史的な都市です",   "category": "city",    "country": "Japan"})
    engine.add_json({"id": "2", "body": "任天堂の本社は京都にあります",   "category": "company", "country": "Japan"})
    engine.add_json({"id": "3", "body": "東京は日本の首都です",           "category": "city",    "country": "Japan"})
    engine.add_json({"id": "4", "body": "パリはフランスの首都です",       "category": "city",    "country": "France"})
    engine.commit()

    # "京都" かつ category=company → id=2 のみ
    results = engine.search("京都", limit=10, filters={"category": "company"})
    for r in results:
        print(r.id, r.body, r.score)
```

---

## ベクトル検索（KNN）

`SearchEngine` に `vector_dimension` を指定すると KNN ベクトル検索が有効になります。

```python
from nlp4j_local_search import SearchEngine

with SearchEngine("ja", vector_dimension=2) as engine:
    engine.add("1_East",  [ 1.0,  0.0])
    engine.add("2_North", [ 0.0,  1.0])
    engine.add("3_West",  [-1.0,  0.0])
    engine.add("4_South", [-1.0, -1.0])
    engine.commit()

    # クエリベクトルに近い順（コサイン類似度）で返る
    results = engine.search([0.9, 0.1], limit=4)
    for r in results:
        print(r.id, r.score)
```

### Embedding ベクトルとの組み合わせ例

```python
from nlp4j_local_search import SearchEngine

vector_dim = 768  # BERT など

with SearchEngine("ja", vector_dimension=vector_dim) as engine:
    engine.add("doc1", embedding_vector_1)
    engine.add("doc2", embedding_vector_2)
    engine.add("doc3", embedding_vector_3)
    engine.commit()

    results = engine.search(query_embedding_vector, limit=5)
    for r in results:
        print(r.id, r.score)
```

---

## フィールド付きベクトル検索

ベクトル登録時に `fields` を付け、検索時に `filters` を指定することで、
フィールド条件を満たすドキュメントの中から上位 k 件を返します。

フィルターはベクトル検索の後処理ではなく、KNN クエリの内部で適用されます。
そのため、指定した `limit` 件の結果を正しく取得できます。

```python
from nlp4j_local_search import SearchEngine

with SearchEngine("ja", vector_dimension=2) as engine:
    engine.add("1_tech_East",   [ 1.0,  0.0], fields={"category": "tech",   "country": "Japan"})
    engine.add("2_tech_North",  [ 0.0,  1.0], fields={"category": "tech",   "country": "Japan"})
    engine.add("3_travel_East", [ 0.9,  0.2], fields={"category": "travel", "country": "Japan"})
    engine.add("4_travel_West", [-1.0,  0.0], fields={"category": "travel", "country": "France"})
    engine.add("5_tech_NE",     [ 0.7,  0.7], fields={"category": "tech",   "country": "USA"})
    engine.commit()

    query_vector = [0.9, 0.1]

    # フィルターなし: 全ドキュメントを類似度順
    results = engine.search(query_vector, limit=10)

    # category=tech のみ: tech ドキュメントの中から類似度順
    results = engine.search(query_vector, limit=10, filters={"category": "tech"})

    # 複数フィールド（AND）
    results = engine.search(query_vector, limit=10,
                            filters={"category": "tech", "country": "Japan"})

    for r in results:
        print(r.id, r.score)
```

---

## 言語設定

日本語：

```python
engine = SearchEngine("ja")
```

英語：

```python
engine = SearchEngine("en")
```

---

## 日本語検索の特性：単純な部分一致との違い

日本語の検索では、単純な文字列の部分一致を使うとノイズが発生することがあります。

例えば `京都` で部分一致検索をすると、`東京都` にも `京都` という文字が含まれるためヒットしてしまいます。

```python
"京都" in "東京都"  # True
```

しかし、全文検索エンジンでは Analyzer によって語を分解してからインデックスするため、`東京都` と `京都` を別の語として扱えます。

```python
from nlp4j_local_search import SearchEngine

with SearchEngine("ja") as engine:
    engine.add("1", "東京都は日本の都道府県のひとつです")
    engine.add("2", "京都は日本の都市です")
    engine.add("3", "京都市には任天堂の本社があります")

    engine.commit()

    for r in engine.search("京都", limit=10):
        print(r.id, r.body, r.score)
```

`SearchEngine("ja")` は日本語向け Analyzer を使うため、`東京都` が `京都` のノイズとしてヒットしにくくなります。

---

## 英語検索の特性：語形の正規化

`SearchEngine("en")` では英語向け Analyzer を使います。

`search`・`searches`・`searched`・`searching` などの語形変化をまとめてマッチさせることができます。

```python
from nlp4j_local_search import SearchEngine

with SearchEngine("en") as engine:
    engine.add("1", "Developers are searching documents with a local search engine.")
    engine.add("2", "A developer searched many documents yesterday.")
    engine.add("3", "This tool searches local JSON documents.")

    engine.commit()

    for r in engine.search("search", limit=10):
        print(r.id, r.body, r.score)
```

---

## `view()` — インデックスの中身を概観する

`view()` はインデックスに格納されたデータをひと目で把握するための inspection API です。

**count モード** — Lucene クエリなし：

```python
from nlp4j_local_search import SearchEngine

with SearchEngine("en", auto_analyze=False) as engine:
    engine.add_json({"id": "1", "body": "...", "maker": "Nissan", "category": "body",       "part": "door mirror"})
    engine.add_json({"id": "2", "body": "...", "maker": "Nissan", "category": "body",       "part": "door mirror"})
    engine.add_json({"id": "3", "body": "...", "maker": "Nissan", "category": "electrical", "part": "battery"})
    engine.add_json({"id": "4", "body": "...", "maker": "Toyota", "category": "brake",      "part": "brake"})
    engine.add_json({"id": "5", "body": "...", "maker": "Toyota", "category": "electrical", "part": "battery"})
    engine.add_json({"id": "6", "body": "...", "maker": "Honda",  "category": "brake",      "part": "brake"})
    engine.commit()

    # 全 aggregatable フィールドの上位3件を一覧表示
    print(engine.view())
    # View: aggregatable fields
    # Format: field | value (document count)
    #
    # maker    | Nissan (3), Toyota (2), Honda (1)
    # category | brake (2), body (2), electrical (2)
    # part     | brake (2), door mirror (2), battery (2)

    # 単一フィールドを件数降順で表示
    print(engine.view("maker"))
    # View: maker
    # Values are ordered by document count.
    #
    # Rank  Value                   Count
    # ----  -------------------- --------
    #    1  Nissan                      3
    #    2  Toyota                      2
    #    3  Honda                       1
```

**relativeRate モード** — Lucene クエリあり（keyword フィールドにも対応）：

```python
    # Nissan ドキュメント内での part の分布を全体と比較
    print(engine.view("part", "maker:Nissan"))
    # View: part
    # Lucene query: maker:Nissan
    # Matched documents: 3 / 6
    # Values are ordered by relative rate.
    #
    # Rank  Value                   Count  All Count  Relative Rate
    # ----  -------------------- -------- ---------- --------------
    #    1  door mirror                 2          2          2.00x
    #    2  battery                     1          2          1.00x
```

**チェーン操作** — `sort_by()` / `filter()` は元のオブジェクトを変更せず新しい `ViewResult` を返す：

```python
    result = engine.view("part", "maker:Nissan")

    # relative_rate >= 1.5 の bucket のみ残す
    filtered = result.filter(min_relative_rate=1.5)

    # count 昇順で並べ替え
    sorted_asc = result.sort_by("count", descending=False)

    # チェーン: filter → sort_by
    chained = result.filter(min_count=1).sort_by("relative_rate")
```

`view()` の引数：

| 引数 | 型 | 説明 |
|---|---|---|
| `field` | `str`（省略可） | 集計対象フィールド。省略すると全 aggregatable フィールドの概観。 |
| `lucene_query` | `str`（省略可） | Lucene クエリ（keyword フィールドも指定可）。指定すると relativeRate モードになる。 |
| `size` | `int`（省略可） | 表示するバケット数。デフォルト：概観=3、単一フィールド=10。 |
| `candidate_size` | `int`（デフォルト `1000`） | relativeRate 計算の候補数上限（relativeRate モード専用）。 |

戻り値は `ViewResult`。`print(result)` または Jupyter でセルに評価するだけで整形表示される。
内部データは常に完全な値を保持：`result.fields[0].buckets[0].key` は切り詰めなしの完全な値を返す。

---

## Google Colab での利用

```python
!pip install git+https://github.com/oyahiroki/nlp4j-local-search.git
```

その後：

```python
from nlp4j_local_search import SearchEngine

with SearchEngine("ja") as engine:
    engine.add("1", "東京都は日本の都道府県のひとつです")
    engine.add("2", "京都は日本の都市です")
    engine.add("3", "京都市には任天堂の本社があります")
    engine.add_json({"id": "4", "body": "京都府は広いです"})

    engine.commit()

    results = engine.search("京都", limit=10)
    for r in results:
        print(f"ID: {r.id}, Score: {r.score:.4f}")
        print(f"Body: {r.body}")
        print("-" * 50)
```

注意事項：

- Google Colab には Java がプリインストールされているため、追加のセットアップは不要です
- インデックスはオンメモリのため、セッションをリセットするとデータは失われます
- 初回実行時に JVM の起動に数秒かかる場合があります

---

## 設計思想

### ローカル検索

本ライブラリはサーバー型検索エンジンではありません。

以下の環境構築は不要です。

- Elasticsearch
- OpenSearch
- Solr
- Docker

検索エンジンは Python プロセスの内部で動作します。

### オンメモリインデックス

デフォルトでは検索インデックスをメモリ上に構築します。ディスクへの永続化は行いません。

以下の用途に適しています。

- 一時的な実験
- テストコード
- Jupyter Notebook
- Google Colab
- PoC 開発
- ローカル NLP ワークフロー

### Python ファースト API

内部実装は Java と Apache Lucene を利用していますが、公開 API は Python 利用者向けに設計されています。

```python
engine = SearchEngine("ja")
```

これだけで Lucene ベースの検索を Python から利用できます。

---

## ユースケース

### 自然言語処理の実験

テキストデータや辞書データ、NLP の中間結果などから検索可能なインデックスをすばやく作成できます。

### RAG のプロトタイピング

本格的な RAG システムを構築する前に、小〜中規模データセットでローカルキーワード検索の挙動を確認できます。

### Embedding 実験の検索ベースライン

Embedding モデルを評価する際、ベクトル検索の結果と従来のキーワード検索の結果を比較するのに役立ちます。

### テストコード

インデックスがオンメモリのため、自動テスト内で検索インデックスを作成・破棄できます。

---

## 現在のステータス

このプロジェクトは現在アーリー開発段階です。

現在の対応機能：

- Python からのシンプルなローカル全文検索
- 日本語検索
- 英語検索
- JSON ドキュメント入力
- オンメモリインデックス
- フィールド絞り込み（キーワード完全一致・AND 条件）
- ベクトル検索（KNN）
- フィールド付きベクトル検索
- MultiValued フィールド
- Aggregation（`aggregate()` / `aggregate_json()`）
- OpenSearch Query DSL（`search_json()` / `search_response_json()`）
- `view()` inspection API（count モード / relativeRate モード）
- `relative_rate()` / `relative_rate_lucene()` analytics

将来のバージョンで API が変更される可能性があります。

---

## ロードマップ

- ~~PyPI 公開~~ ✓
- ~~ベクトル検索~~ ✓
- ~~フィールド絞り込み~~ ✓
- ~~MultiValued フィールド~~ ✓
- ~~Aggregation~~ ✓
- ~~OpenSearch Query DSL（`search_json` / `search_response_json`）~~ ✓
- ~~`view()` inspection API~~ ✓
- Google Colab サポートの改善
- ディスクへの永続化

---

## プロジェクト情報

パッケージ名：

```text
nlp4j-local-search
```

Python モジュール名：

```python
nlp4j_local_search
```

現在のバージョン：

```text
0.5.1
```

---

## ライセンス

Apache License 2.0

---

## 作者

Hiroki Oya

GitHub: https://github.com/oyahiroki
