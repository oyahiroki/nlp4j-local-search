# nlp4j-local-search — REST API Server

An Elasticsearch / OpenSearch-compatible REST API server for [nlp4j-local-search](https://github.com/oyahiroki/nlp4j-local-search).

---

## Installation

```bash
pip install "nlp4j-local-search[server]"
```

`httpx` is also required when running the test suite:

```bash
pip install "nlp4j-local-search[server]" httpx
```

---

## Quick Start

```bash
nlp4j-local-search-server --lang ja --index myindex --data mydata.jsonl.gz
```

| Option | Default | Description |
|---|---|---|
| `--lang` | *(required)* | Language: `ja` or `en` |
| `--index` | `default` | Index name used in URL paths |
| `--data` | *(none)* | Path to a `.jsonl` or `.jsonl.gz` data file to load on startup |
| `--auto-analyze` | `false` | Enable NLP4J automatic text analysis |
| `--host` | `127.0.0.1` | Bind address |
| `--port` | `9200` | Bind port |

---

## Swagger UI

Starting the server automatically enables Swagger UI — no extra installation or configuration required.

| URL | Description |
|---|---|
| `http://localhost:9200/docs` | **Swagger UI** — browse and execute API requests in the browser |
| `http://localhost:9200/redoc` | ReDoc — alternative documentation viewer |
| `http://localhost:9200/openapi.json` | Raw OpenAPI schema (JSON) |

All endpoints (`/_search`, `/_count`, `/_mapping`) are listed in the UI and can be
called directly from the browser.

### How it works

FastAPI inspects the route definitions in `app.py` and the Pydantic models in
`models.py` at startup, then generates an OpenAPI schema automatically.
Swagger UI reads that schema to render the documentation and request forms.

```
app.py  (route definitions)
models.py  (Pydantic models)
        ↓  auto-analysed by FastAPI
OpenAPI schema  (/openapi.json)
        ↓
Swagger UI  (/docs)
```

> **Note:** Swagger UI loads its JavaScript from a CDN.
> In offline environments `/docs` may not render correctly.

---

## Endpoints

### `GET /`

Returns server info.

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

Returns field mapping for the index.

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

Full-text search via query string parameter.

```bash
curl "http://localhost:9200/myindex/_search?q=fuse+replacement&size=5"
```

---

### `POST /{index}/_search`

Search using a Query DSL body.

**Response format** (all search variants):

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
        "_source": { "body": "...", "maker_s": "NISSAN" }
      }
    ]
  }
}
```

---

### `GET /{index}/_count?q=...`

### `POST /{index}/_count`

Returns the number of matching documents.

```json
{ "count": 123, "_shards": { "total": 1, "successful": 1, "skipped": 0, "failed": 0 } }
```

---

## Query DSL

### `match_all`

```json
{ "query": { "match_all": {} } }
```

### `match` — full-text (TEXT field)

```json
{
  "query": { "match": { "text_ja": "fuse replacement" } },
  "size": 10
}
```

### `match` — vector search (VECTOR field)

When the target field is of type `VECTOR`, the query text is automatically
passed through the configured embedding model and searched via Lucene HNSW.

```json
{
  "query": { "match": { "vector": "fuse replacement" } },
  "size": 10
}
```

With explicit `k` and `num_candidates`:

```json
{
  "query": {
    "match": {
      "vector": {
        "query": "fuse replacement",
        "k": 50,
        "num_candidates": 200
      }
    }
  },
  "size": 10
}
```

`k` controls how many candidates HNSW retrieves; `size` controls how many
results are returned to the client.  `k` must be ≥ `from + size`.

### `knn` — low-level vector search

Use when you need direct control over the query vector.

```json
{
  "query": {
    "knn": {
      "field": "vector",
      "query_text": "fuse replacement",
      "k": 10,
      "num_candidates": 100
    }
  }
}
```

Raw vector input:

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

### `term`

```json
{ "query": { "term": { "maker_s": "NISSAN" } } }
```

### `range`

```json
{ "query": { "range": { "year": { "gte": 2020, "lte": 2025 } } } }
```

Operators: `gt`, `gte`, `lt`, `lte`.

### `query_string`

```json
{ "query": { "query_string": { "query": "text_ja:fuse AND maker_s:NISSAN" } } }
```

### `bool`

```json
{
  "query": {
    "bool": {
      "must":    [ { "match": { "text_ja": "fuse" } } ],
      "filter":  [ { "term":  { "maker_s": "NISSAN" } } ],
      "must_not":[ { "term":  { "maker_s": "TOYOTA" } } ],
      "should":  [ { "term":  { "category_s": "safety" } } ]
    }
  }
}
```

**Vector search with filter:**

```json
{
  "query": {
    "bool": {
      "must":   [ { "match": { "vector": "fuse replacement" } } ],
      "filter": [ { "term":  { "maker_s": "NISSAN" } } ]
    }
  },
  "size": 10
}
```

> **v1 limitation:** `bool.should` combined with a VECTOR query, and hybrid
> BM25 + VECTOR ranking (multiple queries in `must`), are not supported yet.

---

## Source Filtering (`_source`)

```json
{ "query": { "match_all": {} }, "_source": ["title", "maker_s"] }
```

```json
{ "query": { "match_all": {} }, "_source": { "includes": ["title"], "excludes": ["body"] } }
```

```json
{ "query": { "match_all": {} }, "_source": false }
```

---

## Pagination

```json
{ "query": { "match_all": {} }, "size": 20, "from": 40 }
```

---

## Architecture

```
REST Query DSL
      ↓
 QueryPlanner
      ↓
  SearchPlan
  ├─ LexicalSearchPlan  → SearchEngine.search()
  └─ VectorSearchPlan   → SearchEngine.search_vector()
                               ↓
                         Lucene / HNSW
```

`QueryPlanner` inspects the field type via `SearchEngine.field_kind()` (or
`field_info()` if available) and produces the appropriate plan.  The FastAPI
layer never needs to know whether a query is lexical or vector.

---

## Programmatic Usage

```python
from nlp4j_local_search import SearchEngine
from nlp4j_local_search.server import create_app
from nlp4j_local_search.server.service import ServerConfig

config = ServerConfig(lang="ja", index_name="myindex", data_path="data.jsonl.gz")
app = create_app(config)

# Use with uvicorn:
# uvicorn.run(app, host="127.0.0.1", port=9200)
```

---

## Running Tests

```bash
pip install -e ".[server]" httpx pytest
pytest tests/server/
```

Tests in `tests/server/` are JVM-free — `SearchEngine` is mocked.
