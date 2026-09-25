![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-Apache--2.0-green)

https://pypi.org/project/nlp4j-local-search/

https://github.com/oyahiroki/nlp4j-local-search

# nlp4j-local-search

English | [日本語](README_ja.md)


**Use Apache Lucene from Python without running Elasticsearch, OpenSearch, Solr, or Docker.**

`nlp4j-local-search` is a lightweight in-memory full-text search library for Python.

It allows you to use Apache Lucene-based search functionality directly from Python, without setting up a search server.

This library is designed for:

- NLP experiments
- RAG prototyping
- Local full-text search
- Jupyter Notebook and Google Colab experiments
- Small search applications
- Test code that needs temporary search indexes

Internally, it uses Java and Apache Lucene, but Python users do not need to write Java code.

---

## Why this library?

Elasticsearch, OpenSearch, and Apache Solr are powerful search engines, and they are all built on Apache Lucene.

However, for small experiments, local prototypes, or notebook-based workflows, setting up a full search server can be too heavy.

With `nlp4j-local-search`, you can create a Lucene-based search index directly inside your Python process.

```python
from nlp4j_local_search import SearchEngine

with SearchEngine("en") as engine:
    engine.add("1", "Developers are searching documents with a local search engine.")
    engine.add("2", "A developer searched many documents yesterday.")
    engine.add("3", "This tool searches local JSON documents.")

    engine.commit()

    for r in engine.search("search"):
        print(r.id, r.body, r.score)
```

No server.  
No Docker.  
No external search engine process.

---

## Features

- Python-first API
- Apache Lucene-based full-text search
- In-memory local search
- No Elasticsearch / OpenSearch / Solr / Docker required
- Japanese and English full-text search
- JSON document input
- **Field filtering** — filter results by exact-match field values (AND conditions)
- **Vector search (KNN)** — nearest-neighbour search using float vectors
  - Legacy single-field API (`vector_dimension=`)
  - Named multi-field API (`vector_fields=` + `VectorFieldConfig`)
  - `field_info()` — schema metadata (type, dimension, similarity, model)
  - `search_vector(field=..., filter_query=...)` — field-targeted KNN with Lucene filter
  - `search_vector_by_text()` — automatic embedding → KNN search
- **MultiValued fields** — register JSON array fields; each element is indexed as an independent keyword value
- **Aggregation** — terms aggregation (`aggregate()` / `aggregate_json()`)
- **OpenSearch Query DSL** — `search_json()` and `search_response_json()`
- **`view()` inspection API** — browse index content at a glance with `sort_by()` / `filter()` chains
- **REST API server** — Elasticsearch/OpenSearch-compatible REST API with Swagger UI (optional)
- **Interactive CLI** — `nlp4j-local-search` REPL for loading and querying datasets
- **Data CLI** — `nlp4j-data` REPL for inspecting and transforming JSONL files

---

## Installation

```bash
pip install nlp4j-local-search
```

With the REST API server:

```bash
pip install "nlp4j-local-search[server]"
```

## Development version

```bash
git clone https://github.com/oyahiroki/nlp4j-local-search.git
cd nlp4j-local-search
pip install -e .
```

---

## Requirements

- Python 3.9 or later
- Java runtime environment
- jpype1

---

## Quick Start

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

## Japanese Analyzer Example: Avoiding Noisy Substring Matches

Japanese text search is different from simple substring matching.

For example, if you search for `京都` using simple substring matching, a sentence containing `東京都` may also match because `東京都` contains the characters `京都`.

However, with Japanese full-text analysis, `東京都` and `京都` can be treated as different terms.

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

---

## Recommended Usage

Using `SearchEngine` as a context manager is recommended.

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

Example output:

```text
2 京都は日本の都市です。 0.18059490621089935
4 京都府は広いです 0.18059490621089935
3 京都市には任天堂の本社があります 0.16212496161460876
```

---

## Adding Documents

You can add a document by specifying an ID and body text.

```python
engine.add("1", "Kyoto is a historical city in Japan.")
```

You can also attach extra fields to a document for later filtering.

```python
engine.add("1", "Kyoto is a historical city in Japan.",
           fields={"category": "city", "country": "Japan"})
engine.add("2", "Nintendo is headquartered in Kyoto.",
           fields={"category": "company", "country": "Japan"})
```

`fields` values must be strings and are stored as keyword fields (exact-match, not analyzed).
The field names `id`, `body`, and `vector` are reserved and cannot be used.

---

## Adding JSON Documents

You can also add a document as a Python dictionary.

```python
engine.add_json({
    "id": "1",
    "body": "Kyoto is a historical city in Japan.",
    "category": "city",
    "country": "Japan"
})
```

Or as a JSON string.

```python
engine.add_json("""
{
  "id": "2",
  "body": "Osaka is a large city in western Japan.",
  "category": "city",
  "country": "Japan"
}
""")
```

Any JSON key other than `id` and `body` is automatically registered as a keyword field.

---

## Searching

```python
results = engine.search("Kyoto")
```

You can specify the maximum number of results.

```python
results = engine.search("Kyoto", limit=10)
```

Each result has the following attributes:

```python
r.id    # str
r.body  # Optional[str]  — None when the document has no body text
r.score # float
r.data  # Optional[str]  — raw JSON string of the original document (add_json only)
```

---

## Field Filtering

Use the `filters` keyword argument to narrow results by exact field values.
Multiple filters are combined with AND.

```python
# Single filter
results = engine.search("Kyoto", limit=10, filters={"category": "city"})

# Multiple filters (AND)
results = engine.search("Kyoto", limit=10,
                        filters={"category": "city", "country": "Japan"})

# Field-only filter (match_all + filter)
results = engine.search("", limit=10, filters={"country": "Japan"})
```

---

## MultiValued Fields

When a field value in `add_json()` is a JSON array, each element is indexed as an independent keyword value.
One document can appear in multiple aggregation buckets.

```python
engine.add_json({"id": "1", "body": "Kyoto is a historic city.",
                 "tags": ["city", "tourism", "Japan"]})
engine.add_json({"id": "2", "body": "Nintendo is headquartered in Kyoto.",
                 "tags": ["company", "Japan"]})
```

You can filter by any element of a MultiValued field using the standard `filters` argument:

```python
# Returns documents where tags contains "Japan"
results = engine.search("", limit=10, filters={"tags": "Japan"})
```

---

## Aggregation

Use `aggregate()` to count documents per field value (terms aggregation).

```python
with SearchEngine("en") as engine:
    engine.add_json({"id": "1", "body": "Kyoto is a historic city.",
                     "tags": ["city", "tourism", "Japan"]})
    engine.add_json({"id": "2", "body": "Nintendo is headquartered in Kyoto.",
                     "tags": ["company", "Japan"]})
    engine.add_json({"id": "3", "body": "Tokyo is the capital city of Japan.",
                     "tags": ["city", "capital", "Japan"]})
    engine.commit()

    # Count by tags
    response = engine.aggregate("tags", size=10)
    for bucket in response["aggregations"]["tags"]["buckets"]:
        print(bucket["key"], bucket["doc_count"])

    # Pre-filter with full-text query before aggregating
    response = engine.aggregate("tags", size=10, query="Kyoto")
```

`aggregate()` parameters:

| Parameter | Type | Description |
|---|---|---|
| `field` | `str` | Field to aggregate on |
| `name` | `str` (optional) | Aggregation name (defaults to `field`) |
| `size` | `int` (default `10`) | Maximum number of buckets to return |
| `query` | `str` (optional) | Full-text query to pre-filter documents |
| `filters` | `dict[str, str]` (optional) | Field filters to pre-filter documents |

For direct JSON control, use the low-level `aggregate_json()`:

```python
response = engine.aggregate_json({
    "name": "tags",
    "field": "tags",
    "size": 10,
    "query": "Kyoto",
})
```

---

## `view()` — Inspect Index Content

`view()` is an inspection API for browsing what is stored in the index.

**Count mode** — no Lucene query:

```python
from nlp4j_local_search import SearchEngine

with SearchEngine("en", auto_analyze=False) as engine:
    engine.add_json({"id": "1", "body": "...", "maker": "Nissan", "part": "door mirror"})
    engine.add_json({"id": "2", "body": "...", "maker": "Nissan", "part": "door mirror"})
    engine.add_json({"id": "3", "body": "...", "maker": "Nissan", "part": "battery"})
    engine.add_json({"id": "4", "body": "...", "maker": "Toyota", "part": "brake"})
    engine.commit()

    # Overview — top 3 values per aggregatable field
    print(engine.view())

    # Single field — top 10 values in table form
    print(engine.view("maker"))
```

**Relative-rate mode** — with a Lucene query:

```python
    # How distinctive is each part value for Nissan documents vs. all documents?
    print(engine.view("part", "maker:Nissan"))
```

**Chain methods** — `sort_by()` and `filter()` return a new `ViewResult`:

```python
    result = engine.view("part", "maker:Nissan")
    filtered = result.filter(min_relative_rate=1.5)
    sorted_asc = result.sort_by("count", descending=False)
```

`view()` parameters:

| Parameter | Type | Description |
|---|---|---|
| `field` | `str` (optional) | Field to inspect. Omit for overview of all aggregatable fields. |
| `lucene_query` | `str` (optional) | Lucene query to pre-filter documents. Activates relative-rate mode. |
| `size` | `int` (optional) | Number of buckets to display. Default: 3 (overview) or 10 (single field). |
| `candidate_size` | `int` (default `1000`) | Top candidates for relative-rate computation. |

---

## OpenSearch Query DSL

### `search_json()` — returns `list[SearchResult]`

```python
results = engine.search_json({
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
```

### `search_response_json()` — returns the full OpenSearch response `dict`

```python
response = engine.search_response_json({
    "size": 10,
    "query": {"bool": {"filter": [{"term": {"tags": "Japan"}}]}},
})
total = response["hits"]["total"]["value"]
for hit in response["hits"]["hits"]:
    print(hit["_source"]["id"], hit["_source"].get("body"))
```

---

## Vector Search — Legacy API (`vector_dimension`)

Pass `vector_dimension` to enable KNN vector search using the default `"vector"` field.

```python
from nlp4j_local_search import SearchEngine

with SearchEngine("en", vector_dimension=2) as engine:
    engine.add("1_East",  [1.0,  0.0])
    engine.add("2_North", [0.0,  1.0])
    engine.add("3_West",  [-1.0, 0.0])
    engine.commit()

    results = engine.search_vector([0.9, 0.1], limit=10)
    for r in results:
        print(r.id, r.score)
```

Results are returned in descending cosine-similarity order.

---

## Vector Search — Named Field API (`vector_fields`)

Use `VectorFieldConfig` and `vector_fields=` to define one or more named KNN vector fields.
This is the recommended API for new projects.

```python
from nlp4j_local_search import SearchEngine, VectorFieldConfig

with SearchEngine(
    lang="en",
    vector_fields={
        "vector3": VectorFieldConfig(
            dimension=3,
            similarity="cosine",
            model="demo-3d",
        )
    },
) as engine:

    engine.add_json({
        "id": "1",
        "text_en": "Electric vehicle battery",
        "category_s": "vehicle",
        "vector3": [1.0, 0.0, 0.0],
    })
    engine.add_json({
        "id": "2",
        "text_en": "Computer software",
        "category_s": "software",
        "vector3": [0.0, 1.0, 0.0],
    })
    engine.commit()

    # Vector field metadata
    info = engine.field_info("vector3")
    print(info.type)        # VECTOR
    print(info.dimension)   # 3
    print(info.model)       # demo-3d

    # KNN search on a named field
    results = engine.search_vector(
        [1.0, 0.0, 0.0],
        field="vector3",
        limit=10,
    )

    # KNN search with a Lucene query filter
    results = engine.search_vector(
        [1.0, 0.0, 0.0],
        field="vector3",
        limit=10,
        filter_query='category_s:"vehicle"',
    )

    # List all VECTOR fields
    print(engine.vector_fields())  # ['vector3']
```

`VectorFieldConfig` parameters:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `dimension` | `int` | *(required)* | Number of dimensions. Must be > 0. |
| `similarity` | `str` | `"cosine"` | Similarity function: `cosine`, `dot_product`, `euclidean`, `maximum_inner_product`. |
| `model` | `str` | `None` | Optional embedding model identifier stored in the schema. |

---

## Vector Search with Text Query (`search_vector_by_text`)

When an `EmbeddingProvider` is configured, you can search by text directly.

```python
from nlp4j_local_search import SearchEngine, VectorFieldConfig
from my_embedding import MyEmbeddingProvider

embedding = MyEmbeddingProvider()  # must implement embed_query(text) and .dimension

with SearchEngine(
    lang="ja",
    vector_fields={
        "vector1024": VectorFieldConfig(dimension=1024),
    },
    embedding=embedding,
) as engine:

    # ... add documents ...
    engine.commit()

    results = engine.search_vector_by_text(
        "ヒューズの交換",
        field="vector1024",
        limit=10,
        filter_query='maker_s:"ニッサン"',
    )
```

---

## Vector Search with Field Filters (Legacy)

The legacy `filters=` dict is supported for the default `"vector"` field only.
For named fields use `filter_query=` instead.

```python
with SearchEngine("en", vector_dimension=2) as engine:
    engine.add("1", [1.0, 0.0], fields={"category": "tech"})
    engine.add("2", [0.0, 1.0], fields={"category": "travel"})
    engine.commit()

    results = engine.search_vector(
        [0.9, 0.1], limit=10, filters={"category": "tech"}
    )
```

---

## `field_info()` — Schema Metadata

```python
info = engine.field_info("vector3")
# FieldInfo(name='vector3', type='VECTOR', stored=False, aggregatable=False,
#           sortable=False, range=False, multi_valued=False,
#           dimension=3, similarity='cosine', model='demo-3d')

info = engine.field_info("category_s")
# FieldInfo(name='category_s', type='KEYWORD', ...)

engine.field_info("nonexistent")  # None
```

---

## Language Settings

Japanese:

```python
engine = SearchEngine("ja")
```

English:

```python
engine = SearchEngine("en")
```

---

## English Analyzer Example

When using `SearchEngine("en")`, English text is analyzed with an English analyzer.

This means that search can handle common English word variations such as:

- `search` / `searches` / `searched` / `searching`
- `document` / `documents`

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

## Japanese Search Example

```python
from nlp4j_local_search import SearchEngine

with SearchEngine("ja") as engine:
    engine.add("1", "東京都は日本の都道府県のひとつです")
    engine.add("2", "京都は日本の都市です")
    engine.add("3", "京都市には任天堂の本社があります")
    engine.add("4", "大阪は関西の大都市です")
    engine.commit()

    for r in engine.search("京都", limit=10):
        print(r.id, r.body, r.score)
```

---

## Interactive CLI — `nlp4j-local-search`

An interactive REPL for loading JSONL datasets into a local Lucene index and exploring them.

```bash
nlp4j-local-search --lang ja
```

```text
>> load("data.jsonl.gz")
Loaded 30,956 documents in 4.21 seconds (7,353 docs/sec).

>> search("高橋留美子", 5)
[473079] score=8.8259
『勝手なやつら』は、高橋留美子のデビュー作。...

>> view("category_s", 10)
View: category_s
...

>> exit
bye
```

Available commands: `load`, `count`, `fields`, `aggregatable_fields`, `search`, `view`, `help`, `exit`.

See [`src/nlp4j_local_search/cli/search/README.md`](src/nlp4j_local_search/cli/search/README.md) for the full reference.

---

## Data CLI — `nlp4j-data`

An interactive REPL for inspecting, transforming, and exporting JSONL datasets — no JVM required.

```bash
nlp4j-data
```

```text
>> data sample.jsonl
Loaded source: sample.jsonl
Documents: 100

>> attrs
id
title
text
category

>> remove category
Removed: category
id, title, text

>> rename text body
Renamed: text -> body
id, title, body

>> write_jsonl output.jsonl
100

>> exit
```

Available commands: `data`, `attrs`, `head`, `remove`, `rename`, `pipeline`, `undo`, `write_jsonl`, `save_config`, `help`, `exit`.

See [`src/nlp4j_local_search/cli/data/README.md`](src/nlp4j_local_search/cli/data/README.md) for the full reference.

---

## REST API Server

An Elasticsearch/OpenSearch-compatible REST API server with Swagger UI.

Install:

```bash
pip install "nlp4j-local-search[server]"
```

Start:

```bash
nlp4j-local-search-server --lang ja --index myindex --data mydata.jsonl.gz
```

Swagger UI is automatically available at `http://localhost:9200/docs` — no additional setup required.

Supported endpoints:

| Endpoint | Description |
|---|---|
| `GET /` | Server info |
| `GET /{index}/_mapping` | Field mapping |
| `GET /{index}/_search?q=...` | Full-text search (query string) |
| `POST /{index}/_search` | Search with Query DSL |
| `GET /{index}/_count` | Document count |
| `POST /{index}/_count` | Document count with query |

See [`src/nlp4j_local_search/server/README.md`](src/nlp4j_local_search/server/README.md) for the full reference.

---

## Google Colab

`nlp4j-local-search` can also be used in Google Colab.

```python
!pip install git+https://github.com/oyahiroki/nlp4j-local-search.git
```

Then:

```python
from nlp4j_local_search import SearchEngine

with SearchEngine("ja") as engine:
    engine.add("1", "東京都は日本の都道府県のひとつです")
    engine.add("2", "京都は日本の都市です")
    engine.add("3", "京都市には任天堂の本社があります")
    engine.add_json({"id": "4", "body": "京都府は広いです"})

    engine.commit()

    for r in engine.search("京都", limit=10):
        print(f"ID: {r.id}, Score: {r.score:.4f}")
        print(f"Body: {r.body}")
        print("-" * 50)
```

Notes:

- The index is stored in memory.
- If the Colab session is reset, the index will be lost.
- JVM startup may take a few seconds on the first run.

---

## Design Concept

### Local Search

This library is not a search server.

You do not need to run:

- Elasticsearch
- OpenSearch
- Solr
- Docker

The search engine runs inside your Python process.

### In-Memory Index

By default, the search index is created in memory.

This makes the library useful for:

- Temporary experiments
- Unit tests
- Jupyter Notebook
- Google Colab
- Proof-of-concept development
- Local NLP workflows

The index is not persisted to disk by default.

### Python-First API

Although the internal implementation uses Java and Apache Lucene, the public API is designed for Python users.

```python
engine = SearchEngine("en")
```

That is enough to start using Lucene-based search from Python.

---

## Use Cases

### NLP Experiments

You can quickly create a searchable index from text data, Wikipedia-derived datasets, dictionary data, or intermediate NLP results.

### RAG Prototyping

Before building a full RAG system, you can test local keyword search and KNN vector search with small or medium-sized datasets.

### Search Baseline for Embedding Experiments

When evaluating embedding models, it is often useful to compare vector search results with traditional keyword-based full-text search.

### Test Code

Because the index is in memory, you can create and discard search indexes during automated tests.

---

## Current Status

This project is currently in an early development stage.

Current focus:

- Simple local full-text search from Python
- Japanese search and English search
- JSON document input (including MultiValued fields via JSON arrays)
- In-memory indexing
- Field filtering (exact-match keyword filters, AND conditions)
- Vector search — legacy `vector_dimension` API and named-field `vector_fields` API
- Named vector field schema metadata (`field_info()`, `vector_fields()`)
- `search_vector(field=..., filter_query=...)` — field-targeted KNN with Lucene filter
- `search_vector_by_text()` — text → embedding → KNN
- Aggregation (`aggregate()` / `aggregate_json()`)
- OpenSearch Query DSL (`search_json()` / `search_response_json()`)
- `view()` inspection API (count mode and relative-rate mode)
- `relative_rate()` / `relative_rate_lucene()` analytics
- Interactive CLI (`nlp4j-local-search`)
- Data transformation CLI (`nlp4j-data`)
- REST API server with Swagger UI (optional, `[server]` extra)

APIs may change in future versions.

---

## Roadmap

Planned or considered features:

- ~~PyPI release~~ ✓
- ~~Vector search~~ ✓
- ~~Named vector field API (`VectorFieldConfig`, `vector_fields`)~~ ✓
- ~~Field filtering~~ ✓
- ~~MultiValued fields~~ ✓
- ~~Aggregation~~ ✓
- ~~OpenSearch Query DSL (`search_json` / `search_response_json`)~~ ✓
- ~~`view()` inspection API~~ ✓
- ~~Interactive CLI (`nlp4j-local-search`)~~ ✓
- ~~Data CLI (`nlp4j-data`)~~ ✓
- ~~REST API server with Swagger UI~~ ✓
- Improved Google Colab support
- Persistent index (disk-based)

---

## Project Information

Package name:

```text
nlp4j-local-search
```

Python module name:

```python
nlp4j_local_search
```

Current version:

```text
0.5.3
```

---

## License

Apache License 2.0

---

## Author

Hiroki Oya

GitHub:

```text
https://github.com/oyahiroki
```
