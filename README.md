![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-Apache--2.0-green)

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
- No Elasticsearch required
- No OpenSearch required
- No Solr required
- No Docker required
- Japanese full-text search
- English full-text search
- JSON document input
- **Field filtering** — filter results by exact-match field values (AND conditions)
- **Vector search (KNN)** — nearest-neighbour search using float vectors
- **Vector search with field filters** — KNN search scoped to a field-filtered subset
- Useful for NLP and RAG experiments

---

## Installation

```bash
pip install nlp4j-local-search
```

## Development version

```bash
git clone https://github.com/oyahiroki/nlp4j-local-search.git
cd nlp4j-local-search
pip install -e .
```

---

## Requirements

- Python 3.8 or later
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
r.id
r.body
r.score
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

## Vector Search

Pass `vector_dimension` to `SearchEngine` to enable KNN vector search.

```python
from nlp4j_local_search import SearchEngine

with SearchEngine("en", vector_dimension=2) as engine:
    engine.add("1_East",  [1.0,  0.0])
    engine.add("2_North", [0.0,  1.0])
    engine.add("3_West",  [-1.0, 0.0])
    engine.add("4_South", [-1.0, -1.0])
    engine.commit()

    results = engine.search([0.9, 0.1], limit=4)
    for r in results:
        print(r.id, r.score)
```

Results are returned in descending cosine-similarity order.

---

## Vector Search with Field Filters

Attach fields when adding vectors, then pass `filters` at search time.
The filter is applied **inside** the KNN query (not as post-processing), so the top-k
results are taken from the matching subset only.

```python
from nlp4j_local_search import SearchEngine

with SearchEngine("en", vector_dimension=2) as engine:
    engine.add("1_tech_East",   [ 1.0,  0.0], fields={"category": "tech",   "country": "Japan"})
    engine.add("2_tech_North",  [ 0.0,  1.0], fields={"category": "tech",   "country": "Japan"})
    engine.add("3_travel_East", [ 0.9,  0.2], fields={"category": "travel", "country": "Japan"})
    engine.add("4_travel_West", [-1.0,  0.0], fields={"category": "travel", "country": "France"})
    engine.add("5_tech_NE",     [ 0.7,  0.7], fields={"category": "tech",   "country": "USA"})
    engine.commit()

    query_vector = [0.9, 0.1]

    # Without filter: all documents ranked by similarity
    results = engine.search(query_vector, limit=10)

    # With filter: only "tech" documents, ranked by similarity
    results = engine.search(query_vector, limit=10, filters={"category": "tech"})

    # Multiple filters (AND)
    results = engine.search(query_vector, limit=10,
                            filters={"category": "tech", "country": "Japan"})

    for r in results:
        print(r.id, r.score)
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

- `search`
- `searches`
- `searched`
- `searching`

It can also handle cases such as:

- `document` / `documents`
- `Lucene` / `Lucene's`
- uppercase / lowercase differences

This is useful when you want more than simple substring matching.

```python
from nlp4j_local_search import SearchEngine

with SearchEngine("en") as engine:
    engine.add("1", "Developers are searching documents with a local search engine.")
    engine.add("2", "A developer searched many documents yesterday.")
    engine.add("3", "This tool searches local JSON documents.")
    engine.add("4", "Lucene's EnglishAnalyzer is useful for English full-text search.")
    engine.add("5", "The quick brown fox jumps over the lazy dog.")

    engine.commit()

    print("Query: search")
    for r in engine.search("search", limit=10):
        print(r.id, r.body, r.score)

    print("Query: document")
    for r in engine.search("document", limit=10):
        print(r.id, r.body, r.score)

    print("Query: lucene")
    for r in engine.search("lucene", limit=10):
        print(r.id, r.body, r.score)
```

Unlike simple substring matching, English full-text search can match related word forms such as `search`, `searched`, and `searching`.

This makes it useful for local search, NLP experiments, and search baseline evaluation.

---

## Japanese Search Example

For Japanese text, use `SearchEngine("ja")`.

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

This is useful when you want to try Japanese full-text search locally without setting up a search server.

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

    results = engine.search("京都", limit=10)

    for r in results:
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

The index is not persisted to disk.

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

Before building a full RAG system, you can test local keyword search behavior with small or medium-sized datasets.

### Search Baseline for Embedding Experiments

When evaluating embedding models, it is often useful to compare vector search results with traditional keyword-based full-text search.

### Test Code

Because the index is in memory, you can create and discard search indexes during automated tests.

---

## Current Status

This project is currently in an early development stage.

Current focus:

- Simple local full-text search from Python
- Japanese search
- English search
- JSON document input
- In-memory indexing
- Field filtering (exact-match keyword filters, AND conditions)
- Vector search (KNN)
- Vector search with field filters

APIs may change in future versions.

---

## Roadmap

Planned or considered features:

- ~~PyPI release~~ ✓
- ~~Vector search~~ ✓
- ~~Field filtering~~ ✓
- Improved Google Colab support
- Aggregation
- JSON Query DSL (`search_json`)
- OpenSearch-compatible API

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
0.3.0
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

