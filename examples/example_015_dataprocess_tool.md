# nlp4j-data: An Interactive Shell for JSONL Data Preparation

`nlp4j-data` is a lightweight interactive shell bundled with
[nlp4j-local-search](https://github.com/oyahiroki/nlp4j-local-search) that
lets you open, inspect, and transform JSONL files — field by field, step by
step — before saving the results.

Every change is previewed instantly.

---

## Installation

`nlp4j-data` is installed automatically with the package:

```bash
pip install nlp4j-local-search
```

Once installed, start the shell with:

```bash
nlp4j-data
```

You will see:

```
nlp4j-data 0.1.0
Type 'help' or '?' for available commands.

>>
```

---

## Quick start — a complete session

Suppose you have the following raw JSONL file:

```jsonl
{"id":1,"category":"city","text":"this is test 1.","xxx":"aaa"}
{"id":2,"category":"company","text":"this is test 2.","xxx":"aaa"}
{"id":3,"category":"city","text":"this is test 3.","xxx":"aaa"}
```

Here is a typical session from opening the file to saving the result:

```
$ nlp4j-data

nlp4j-data 0.1.0
Type 'help' or '?' for available commands.

>> data test.jsonl
Loaded source: test.jsonl
Documents: 3

>> attrs
id
category
text
xxx

>> head 1
{"id": 1, "category": "city", "text": "this is test 1.", "xxx": "aaa"}

>> remove xxx
Removed: xxx
id, category, text

>> rename text text_en
Renamed: text -> text_en
id, category, text_en

>> rename category category_s
Renamed: category -> category_s
id, category_s, text_en

>> head 1
{"id": 1, "category_s": "city", "text_en": "this is test 1."}

>> write_jsonl test2.jsonl
Wrote 3 documents to test2.jsonl in 0.00 seconds.

>> exit
```

The resulting `test2.jsonl` contains:

```jsonl
{"id": 1, "category_s": "city", "text_en": "this is test 1."}
{"id": 2, "category_s": "company", "text_en": "this is test 2."}
{"id": 3, "category_s": "city", "text_en": "this is test 3."}
```

The original `test.jsonl` is **never modified**.

---

## Command reference

### `data <path>`

Open a JSONL file as the data source.

```
>> data test.jsonl
Loaded source: test.jsonl
Documents: 3
```

### `attrs`

Show the current field names.  
The list reflects any `remove` or `rename` operations already applied.

```
>> attrs
id
category
text
xxx
```

### `head [n]`

Preview the first `n` transformed documents (default: 1).  
The output is the result of applying **all transforms defined so far** — it is
always a live preview of the current pipeline state.

```
>> head 2
{"id": 1, "category": "city", "text": "this is test 1.", "xxx": "aaa"}
{"id": 2, "category": "company", "text": "this is test 2.", "xxx": "aaa"}
```

### `remove <field> [field ...]`

Remove one or more fields from every document.  
Multiple fields can be removed in a single command.

```
>> remove xxx debug_flag
Removed: xxx, debug_flag
id, category, text
```

### `rename <from> <to>`

Rename a field.  
Use quotes around field names that contain spaces.

```
>> rename text text_en
Renamed: text -> text_en
id, category, text_en

>> rename "original name" new_name
Renamed: original name -> new_name
```

### `pipeline`

Display the full transformation pipeline built so far: the source file and
every transform in the order it was added.

```
>> pipeline
Source:
  test.jsonl

Transforms:
  1. remove xxx
  2. rename text -> text_en
  3. rename category -> category_s
```

### `undo`

Roll back the last transformation.  
Because `nlp4j-data` stores an undo history, you can step back through
changes freely.

```
>> remove xxx
>> rename text text_en
>> undo
Undone. Current attrs: id, category, text
```

### `write_jsonl <path>`

Execute the pipeline and write the transformed documents to a JSONL file.  
This is the **terminal operation** — actual processing happens here.

```
>> write_jsonl test2.jsonl
Wrote 3 documents to test2.jsonl in 0.01 seconds.
```

### `save_config <path>`

Save the current pipeline definition as a JSON file.  
The config captures the source path and every transform so the pipeline can
be documented or replicated.

```
>> save_config settings.json
Config saved: settings.json
```

The generated `settings.json` looks like:

```json
{
  "version": 1,
  "source": {
    "type": "jsonl",
    "path": "test.jsonl"
  },
  "transforms": [
    { "type": "remove", "fields": ["xxx"] },
    { "type": "rename", "source": "text",     "target": "text_en" },
    { "type": "rename", "source": "category", "target": "category_s" }
  ]
}
```

### `help` / `?`

Show the list of all available commands.

```
>> help
```

Get help for a specific command:

```
>> help rename
>> ? remove
```

### `exit` / `quit`

Exit the shell.

---

## Live preview — the key feature

Every call to `head` and `attrs` reflects the **current pipeline state**,
not the original file.  This means you can experiment interactively:

```
>> data test.jsonl
>> head 1
{"id": 1, "category": "city", "text": "this is test 1.", "xxx": "aaa"}

>> remove xxx
>> head 1
{"id": 1, "category": "city", "text": "this is test 1."}

>> rename text body
>> head 1
{"id": 1, "category": "city", "body": "this is test 1."}
```

If the result looks wrong, just `undo` and try again — no file has been
touched yet.

---

## Using `save_config` and `write_jsonl` together

A typical production workflow:

```
>> data input.jsonl
>> remove internal_id debug_flag
>> rename category category_s
>> rename text body
>> pipeline
>> save_config pipeline_v1.json
>> write_jsonl output.jsonl
>> exit
```

This leaves you with two files:

- `output.jsonl` — the cleaned, renamed dataset ready for indexing
- `pipeline_v1.json` — a reproducible record of exactly what was done

---

## Python API equivalent

Every session in `nlp4j-data` has a direct equivalent in the Python API.
`nlp4j-data` uses the same `DataPipeline` engine internally, so anything
you prototype interactively can be translated directly into code.

### Pure Python — no SearchEngine, no JVM required

This is the closest equivalent to the CLI: pure data preparation without
any search index.

```python
from nlp4j_local_search import data

result = (
    data("input.jsonl")
        .remove("internal_id", "debug_flag")
        .rename("category", "category_s")
        .rename("text", "body")
        .save_config("pipeline_v1.json")
        .write_jsonl("output.jsonl")
)
print(result)
# Wrote 3 documents to output.jsonl in 0.01 seconds.
```

### LocalSearch integration — load into the search index

When you also want to index the data for search, attach a `SearchEngine`:

```python
from nlp4j_local_search import SearchEngine

with SearchEngine("en", auto_analyze=False) as engine:
    result = (
        engine.data("input.jsonl")
              .remove("internal_id", "debug_flag")
              .rename("category", "category_s")
              .rename("text", "body")
              .save_config("pipeline_v1.json")
              .load()           # indexes into Lucene (JVM required)
    )
    print(result)
    # Loaded 3 documents in 0.01 seconds.
```

The key difference:

| | Pure Python (`data()`) | LocalSearch (`engine.data()`) |
|---|---|---|
| JVM required | No | Yes |
| `write_jsonl()` | ✓ | ✓ |
| `load()` | ✗ (raises error) | ✓ |
| `search()` / `view()` | ✗ | ✓ |

---

## Summary

| Task | Command |
|---|---|
| Open a JSONL file | `data <path>` |
| Inspect field names | `attrs` |
| Preview documents | `head [n]` |
| Remove a field | `remove <field>` |
| Rename a field | `rename <from> <to>` |
| Check pipeline steps | `pipeline` |
| Roll back last step | `undo` |
| Save transformed JSONL | `write_jsonl <path>` |
| Save pipeline config | `save_config <path>` |
| Get help | `help` / `?` |
| Exit | `exit` |
