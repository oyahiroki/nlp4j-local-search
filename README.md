# nlp4j-local-search

English | [日本語](README_ja.md)

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-Apache--2.0-green)

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
- Useful for NLP and RAG experiments

---

## Installation

> Note: PyPI release is under preparation.  
> For now, please install directly from GitHub.

```bash
pip install git+https://github.com/oyahiroki/nlp4j-local-search.git
```

For development:

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

---

## Adding JSON Documents

You can also add a document as a Python dictionary.

```python
engine.add_json({
    "id": "1",
    "body": "Kyoto is a historical city in Japan."
})
```

Or as a JSON string.

```python
engine.add_json("""
{
  "id": "2",
  "body": "Osaka is a large city in western Japan."
}
""")
```

This is useful for NLP workflows where JSON and JSONL are commonly used as intermediate data formats.

---

## Searching

```python
results = engine.search("Kyoto")
```

You can specify the maximum number of search results.

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

APIs may change in future versions.

---

## Roadmap

Planned or considered features:

- PyPI release
- Improved Google Colab support
- Vector search
- Aggregation
- JSON Query DSL
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
0.1.0
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

