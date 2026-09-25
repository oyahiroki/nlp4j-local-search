# nlp4j-local-search — REST API サーバー

[nlp4j-local-search](https://github.com/oyahiroki/nlp4j-local-search) 向けの Elasticsearch / OpenSearch 互換 REST API サーバーです。

---

## インストール

```bash
pip install "nlp4j-local-search[server]"
```

テストスイートを実行する場合は `httpx` も必要です。

```bash
pip install "nlp4j-local-search[server]" httpx
```

---

## クイックスタート

```bash
nlp4j-local-search-server --lang ja --index myindex --data mydata.jsonl.gz
```

| オプション | デフォルト | 説明 |
|---|---|---|
| `--lang` | *(必須)* | 言語: `ja` または `en` |
| `--index` | `default` | URL パスで使用するインデックス名 |
| `--data` | *(なし)* | 起動時に読み込む `.jsonl` または `.jsonl.gz` ファイルのパス |
| `--auto-analyze` | `false` | NLP4J 自動テキスト解析を有効にする |
| `--host` | `127.0.0.1` | バインドアドレス |
| `--port` | `9200` | バインドポート |

---

## Swagger UI

サーバーを起動すると、**追加のインストールや設定なし**で Swagger UI が自動的に利用できます。

| URL | 内容 |
|---|---|
| `http://localhost:9200/docs` | **Swagger UI**（ブラウザ上で API を操作・実行） |
| `http://localhost:9200/redoc` | ReDoc（別形式のドキュメント） |
| `http://localhost:9200/openapi.json` | OpenAPI スキーマ（JSON） |

Swagger UI では、すべてのエンドポイント（`/_search`、`/_count`、`/_mapping`）が一覧表示され、
ブラウザ上から直接リクエストを送信して動作を確認できます。

### 仕組み

FastAPI が起動時にコードを解析し、OpenAPI スキーマを自動生成します。
Swagger UI はそのスキーマを読み込んでドキュメントと操作画面を表示します。

```
app.py（エンドポイント定義）
models.py（Pydantic モデル）
        ↓ FastAPI が自動解析
OpenAPI スキーマ（/openapi.json）
        ↓
Swagger UI（/docs）
```

> **注意:** Swagger UI の表示には CDN からの JavaScript 読み込みが必要です。
> オフライン環境では `/docs` が正しく表示されない場合があります。

---

## エンドポイント一覧

### `GET /`

サーバー情報を返します。

```json
{
  "name": "nlp4j-local-search",
  "cluster_name": "nlp4j-local-search",
  "version": { "distribution": "nlp4j-local-search" },
  "tagline": "Local Lucene search with NLP4J"
}
```

---

### `GET /{index}/_mapping`

インデックスのフィールドマッピングを返します。

```bash
curl http://localhost:9200/myindex/_mapping
```

```json
{
  "myindex": {
    "mappings": {
      "properties": {
        "text_ja": { "type": "text" },
        "maker_s": { "type": "keyword" },
        "vector":  { "type": "dense_vector", "dims": 1024, "similarity": "cosine" }
      }
    }
  }
}
```

---

### `GET /{index}/_search?q=...&size=10&from=0`

クエリ文字列パラメータによる全文検索。

```bash
curl "http://localhost:9200/myindex/_search?q=ヒューズ交換&size=5"
```

---

### `POST /{index}/_search`

Query DSL ボディによる検索。

**レスポンス形式**（全検索バリアント共通）:

```json
{
  "took": 3,
  "timed_out": false,
  "_shards": { "total": 1, "successful": 1, "skipped": 0, "failed": 0 },
  "hits": {
    "total": { "value": 42, "relation": "eq" },
    "max_score": 1.23,
    "hits": [
      {
        "_index": "myindex",
        "_id": "doc1",
        "_score": 1.23,
        "_source": { "body": "...", "maker_s": "ニッサン" }
      }
    ]
  }
}
```

---

### `GET /{index}/_count?q=...`

### `POST /{index}/_count`

マッチした文書数を返します。

```json
{ "count": 123, "_shards": { "total": 1, "successful": 1, "skipped": 0, "failed": 0 } }
```

---

## Query DSL

### `match_all` — 全件取得

```json
{ "query": { "match_all": {} } }
```

---

### `match` — 全文検索（TEXT フィールド）

```json
{
  "query": { "match": { "text_ja": "ヒューズの交換" } },
  "size": 10
}
```

---

### `match` — ベクトル検索（VECTOR フィールド）

対象フィールドが `VECTOR` 型の場合、クエリテキストは自動的にエンベディングモデルを
通じてベクトル化され、Lucene HNSW による近傍検索が実行されます。

```json
{
  "query": { "match": { "vector": "ヒューズの交換" } },
  "size": 10
}
```

`k`（HNSW 取得候補数）と `num_candidates` を明示指定する場合:

```json
{
  "query": {
    "match": {
      "vector": {
        "query": "ヒューズの交換",
        "k": 50,
        "num_candidates": 200
      }
    }
  },
  "size": 10
}
```

`k` は HNSW が取得する候補件数、`size` はクライアントに返す件数です。  
`k` は `from + size` 以上である必要があります。

---

### `knn` — 低レベルベクトル検索

クエリベクトルを直接制御したい場合に使用します。

```json
{
  "query": {
    "knn": {
      "field": "vector",
      "query_text": "ヒューズの交換",
      "k": 10,
      "num_candidates": 100
    }
  }
}
```

生ベクトルを直接指定する場合:

```json
{
  "query": {
    "knn": {
      "field": "vector",
      "query_vector": [0.123, -0.456, 0.789],
      "k": 10
    }
  }
}
```

---

### `term` — キーワード完全一致

```json
{ "query": { "term": { "maker_s": "ニッサン" } } }
```

---

### `range` — 数値・日付範囲

```json
{ "query": { "range": { "year": { "gte": 2020, "lte": 2025 } } } }
```

演算子: `gt`（より大きい）、`gte`（以上）、`lt`（未満）、`lte`（以下）。

---

### `query_string` — Lucene クエリ直接指定

```json
{ "query": { "query_string": { "query": "text_ja:ヒューズ AND maker_s:ニッサン" } } }
```

---

### `bool` — 複合クエリ

```json
{
  "query": {
    "bool": {
      "must":    [ { "match": { "text_ja": "ヒューズ" } } ],
      "filter":  [ { "term":  { "maker_s": "ニッサン" } } ],
      "must_not":[ { "term":  { "maker_s": "トヨタ" } } ],
      "should":  [ { "term":  { "category_s": "安全" } } ]
    }
  }
}
```

**VECTOR 検索 + フィルター:**

```json
{
  "query": {
    "bool": {
      "must":   [ { "match": { "vector": "ヒューズの交換" } } ],
      "filter": [ { "term":  { "maker_s": "ニッサン" } } ]
    }
  },
  "size": 10
}
```

> **v1 の制限:** VECTOR クエリと `bool.should` の組み合わせ、および BM25 + VECTOR の
> ハイブリッドランキング（`must` に複数クエリ）は未対応です。

---

## ソースフィルタリング（`_source`）

返すフィールドを絞り込む場合に使用します。

```json
{ "query": { "match_all": {} }, "_source": ["title", "maker_s"] }
```

include / exclude を個別に指定する場合:

```json
{ "query": { "match_all": {} }, "_source": { "includes": ["title"], "excludes": ["body"] } }
```

`_source` を返さない場合:

```json
{ "query": { "match_all": {} }, "_source": false }
```

---

## ページネーション

```json
{ "query": { "match_all": {} }, "size": 20, "from": 40 }
```

---

## アーキテクチャ

```
REST Query DSL
      ↓
 QueryPlanner
      ↓
  SearchPlan
  ├─ LexicalSearchPlan  → SearchEngine.search()       → Lucene
  └─ VectorSearchPlan   → SearchEngine.search_vector() → Lucene HNSW
```

`QueryPlanner` は `SearchEngine.field_kind()`（または `field_info()` が利用可能であればそちら）
でフィールドタイプを取得し、適切なプランを生成します。
FastAPI 層はクエリが字句検索かベクトル検索かを意識しません。

### 将来の拡張

`SearchPlan` 層を導入しているため、今後 `HybridSearchPlan` や `RerankSearchPlan` を
追加しても REST API の基本構造を変更する必要がありません。
例えば以下のようなハイブリッドクエリも将来対応可能です。

```json
{
  "query": {
    "hybrid": {
      "queries": [
        { "match": { "text_ja": "ヒューズ交換" } },
        { "match": { "vector":  "ヒューズ交換" } }
      ]
    }
  }
}
```

---

## プログラムからの利用

```python
from nlp4j_local_search import SearchEngine
from nlp4j_local_search.server import create_app
from nlp4j_local_search.server.service import ServerConfig

config = ServerConfig(lang="ja", index_name="myindex", data_path="data.jsonl.gz")
app = create_app(config)

# uvicorn での起動例:
# uvicorn.run(app, host="127.0.0.1", port=9200)
```

---

## テストの実行

```bash
pip install -e ".[server]" httpx pytest
pytest tests/server/
```

`tests/server/` 内のテストは JVM 不要です。`SearchEngine` はすべてモックで動作します。

---

## ディレクトリ構成

```
nlp4j_local_search/
└── server/
    ├── __init__.py   # lazy import（fastapi 未インストール環境でも利用可）
    ├── models.py     # Pydantic モデル（SearchRequest, CountRequest, SourceFilter）
    ├── plan.py       # SearchPlan データクラス
    ├── query.py      # QueryPlanner（Query DSL → SearchPlan 変換）
    ├── service.py    # SearchService（検索・count・mapping 実行）
    ├── app.py        # FastAPI エンドポイント定義
    └── main.py       # CLI エントリポイント
```
