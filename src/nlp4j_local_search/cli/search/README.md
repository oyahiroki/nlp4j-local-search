# nlp4j-local-search CLI

`nlp4j-local-search` provides an interactive command-line interface for loading local JSONL datasets into Lucene and exploring them with full-text search, structured field queries, date ranges, aggregations, and relative-rate analysis.

The CLI is designed as a lightweight local search console on top of `nlp4j-local-search`.

## Start the CLI

A language must be specified when starting the CLI.

```bash
nlp4j-local-search --lang ja
```

For English:

```bash
nlp4j-local-search --lang en
```

To enable NLP4J automatic linguistic analysis:

```bash
nlp4j-local-search --lang ja --auto-analyze
```

Without `--lang`, the CLI prints its command-line help and exits.

Example:

```text
$ nlp4j-local-search --lang ja
nlp4j-local-search
Language: ja
Auto analyze: False
Type 'help' or '?' for help.

>>
```

## Interactive help

At the prompt, type:

```text
>> help
```

or:

```text
>> ?
```

to display the available commands and examples.

## Load a JSONL file

Use `load()` to load a JSONL dataset and create a searchable local Lucene index.

```text
>> load("data.jsonl")
```

Gzip-compressed JSONL files are also supported:

```text
>> load("data.jsonl.gz")
```

The loader processes documents as a stream, so the entire JSONL file does not need to be loaded into memory at once.

After loading, the CLI reports the number of documents, elapsed time, and indexing throughput.

Example:

```text
>> load("examples_demo/jawiki-20260801-pages-articles_compact_manga.jsonl.gz")
Loaded 30,956 documents in 4.21 seconds (7,353 docs/sec).
```

Loading another file replaces the current in-memory search engine with a new one.

### File-name completion

Inside `load("...")`, press `Tab` to complete file and directory names.

For example:

```text
>> load("exa<Tab>
```

may become:

```text
>> load("examples_demo/
```

and continuing with `Tab` can complete the file name.

## Show document count

```text
>> count
```

or:

```text
>> count()
```

Example:

```text
30,956
```

## Show indexed fields

```text
>> fields
```

Example fields may include:

```text
id
body
text
text_en
text_ja
category_s
title_s
timestamp_dt
timestamp_year_i
timestamp_month_i
timestamp_day_i
timestamp_dow_i
timestamp_hour_i
```

The exact fields depend on the loaded dataset.

## Show aggregatable fields

Use:

```text
>> aggregatable_fields
```

to list fields that can be used by aggregation and `view()`.

## Search

The CLI accepts Lucene Query Parser syntax.

### Basic full-text search

```text
>> search("高橋留美子")
```

By default, up to 10 results are returned.

Example output:

```text
[473079] score=8.8259
『勝手なやつら』は、高橋留美子のデビュー作。...

[1107674] score=8.0045
『笑う標的』は、高橋留美子の漫画作品。
```

### Limit the number of results

```text
>> search("高橋留美子", 5)
```

### Phrase search

Use Lucene phrase syntax inside the query string:

```text
>> search('text_ja:"週刊少年サンデー"')
```

### Search a specific field

```text
>> search("category_s:恋愛漫画")
```

### Boolean queries

```text
>> search("高橋留美子 AND 星")
```

You can also combine full-text and structured fields:

```text
>> search("text_ja:高橋留美子 AND category_s:恋愛漫画")
```

### Date-range search

For date fields:

```text
>> search("timestamp_dt:[2026-01-01 TO *]")
```

For derived integer fields:

```text
>> search("timestamp_year_i:[2020 TO 2026]", 20)
```

Lucene Query Parser syntax can therefore be used for:

- simple keyword search
- phrase search
- field-specific search
- `AND`, `OR`, and `NOT`
- structured keyword fields
- numeric ranges
- date ranges

## Explore field values with `view()`

`view()` provides a compact way to inspect frequently occurring field values.

### Show the most common values

```text
>> view("category_s")
```

Example:

```text
View: category_s
Values are ordered by document count.

Rank  Value                   Count
----  -------------------- --------
   1  日本の漫画家                   7007
   2  存命人物                     7005
   3  生年未記載                    2644
   4  継続中の作品                   1857
   5  恋愛漫画                     1639
```

### Specify the number of values

```text
>> view("category_s", 20)
```

### Filter out rare values

The third argument can be used as `min_count`.

```text
>> view("category_s", 20, 3)
```

This is useful when you want to suppress categories that occur only once or twice.

## Analyze characteristic values

`view()` can also analyze values within documents matching a Lucene query.

```text
>> view("category_s", 'text_ja:"高橋留美子"', 20, 3)
```

Arguments:

```text
view("field", "lucene query", size, min_count)
```

For example:

```text
>> view("category_s", 'text_ja:"高橋留美子"', 20, 3)
```

This searches for documents matching `text_ja:"高橋留美子"` and then examines the `category_s` values that characterize those documents.

The result may include:

- count within the matched documents
- count within the complete dataset
- relative rate

A high relative rate indicates that a value occurs more frequently in the matched subset than in the dataset overall.

Using `min_count` is often useful because very rare values can otherwise receive high relative-rate values.

## Supported `view()` forms

```text
view("field")
view("field", size)
view("field", size, min_count)

view("field", "lucene query")
view("field", "lucene query", size)
view("field", "lucene query", size, min_count)
```

Examples:

```text
>> view("category_s")
>> view("category_s", 20)
>> view("category_s", 20, 3)
>> view("category_s", 'text_ja:"高橋留美子"')
>> view("category_s", 'text_ja:"高橋留美子"', 20)
>> view("category_s", 'text_ja:"高橋留美子"', 20, 3)
```

## Exit

Use either:

```text
>> exit
```

or:

```text
>> quit
```

The CLI closes the current search engine and exits.

```text
>> exit
bye
```

## Example session

```text
$ nlp4j-local-search --lang ja
nlp4j-local-search
Language: ja
Auto analyze: False
Type 'help' or '?' for help.

>> load("examples_demo/jawiki-20260801-pages-articles_compact_manga.jsonl.gz")
Loaded 30,956 documents in 4.21 seconds (7,353 docs/sec).

>> count
30,956

>> fields
id
body
text
text_en
text_ja
category_s
title_s
timestamp_dt
...

>> search("高橋留美子", 5)
[473079] score=8.8259
『勝手なやつら』は、高橋留美子のデビュー作。...

...

>> search("category_s:恋愛漫画", 5)
...

>> search("timestamp_dt:[2026-01-01 TO *]", 5)
...

>> view("category_s", 10)
View: category_s
Values are ordered by document count.
...

>> view("category_s", 'text_ja:"高橋留美子"', 20, 3)
View: category_s
Lucene query: text_ja:"高橋留美子"
...

>> exit
bye
```

## Command summary

| Command | Description |
|---|---|
| `help` / `?` | Show interactive help |
| `load("file.jsonl")` | Load a JSONL dataset |
| `load("file.jsonl.gz")` | Load a gzip-compressed JSONL dataset |
| `count` | Show document count |
| `fields` | Show indexed fields |
| `aggregatable_fields` | Show fields available for aggregation |
| `search("query")` | Search with Lucene Query Parser syntax |
| `search("query", limit)` | Search with a result limit |
| `view("field")` | Show common field values |
| `view("field", size, min_count)` | Show common values with filtering |
| `view("field", "query", size, min_count)` | Analyze characteristic values for matching documents |
| `exit` / `quit` | Exit the CLI |

## Notes

The CLI intentionally exposes Lucene Query Parser syntax rather than hiding it behind a separate query language. This makes it possible to use simple keyword queries and structured field/range queries from the same interactive console.

The loaded index is local to the running CLI process unless additional index persistence features are used separately through the Python API.
