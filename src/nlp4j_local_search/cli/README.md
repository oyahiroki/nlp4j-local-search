# nlp4j_local_search.cli

Command-line tools and interactive utilities for `nlp4j-local-search`.

---

## Directory Structure

```text
src/nlp4j_local_search/cli/
├── __init__.py           # Package entry and re-exports
├── README.md             # This documentation
├── data/                 # nlp4j-data: Interactive data manipulation REPL
│   ├── __init__.py
│   ├── context.py        # DataShellContext (state & undo stack)
│   ├── commands.py       # Command implementations (Command Pattern)
│   └── shell.py          # DataShell REPL loop & main()
└── search/               # nlp4j-local-search: Local search CLI
    ├── __init__.py
    └── main.py           # CLI argument parsing & main entry point
```

---

## Command-Line Scripts

| Command | Entry Point | Description |
|---|---|---|
| `nlp4j-data` | `nlp4j_local_search.cli.data.shell:main` | Interactive REPL for inspecting, transforming, and saving JSONL datasets. |
| `nlp4j-local-search` | `nlp4j_local_search.cli.search.main:main` | CLI command for search operations using local search engine. |

---

## 1. Data Manipulation Shell (`nlp4j-data`)

### Overview
`nlp4j-data` allows users to interactively load JSONL datasets, inspect attributes, preview records, apply transformation operations (such as removing or renaming fields), undo operations, and export transformed data or pipeline configurations.

### Launching the Shell

```bash
nlp4j-data
```

Or via Python:

```bash
python -m nlp4j_local_search.cli.data.shell
```

### Available Commands

| Command | Syntax | Description |
|---|---|---|
| `data` | `data <path>` | Opens a JSONL file as the active data source and clears history. |
| `attrs` | `attrs` | Displays all attribute/field names of the transformed document. |
| `head` | `head [n]` | Previews the first `n` transformed documents in JSON format (default: 1). |
| `remove` | `remove <field> [field ...]` | Removes one or more fields from every document and pushes state to undo history. |
| `rename` | `rename <from> <to>` | Renames a field and pushes state to undo history. |
| `pipeline` | `pipeline` | Displays the current data source and applied transformation chain. |
| `undo` | `undo` | Reverts the last transformation step. |
| `write_jsonl` | `write_jsonl <path>` | Writes the transformed documents to a destination JSONL file. |
| `save_config`| `save_config <path>` | Exports the current pipeline configuration to a JSON file. |
| `help` / `?` | `help [command]` | Shows a list of available commands or usage help for a specific command. |
| `exit` / `quit` | `exit` or `quit` | Exits the interactive shell. |

### Usage Example

```text
>> data sample.jsonl
Loaded source: sample.jsonl
Documents: 100

>> attrs
id
title
text
unwanted_field

>> head 1
{"id": 1, "title": "First Document", "text": "Hello world", "unwanted_field": "temp"}

>> remove unwanted_field
Removed: unwanted_field
id, title, text

>> rename text body
Renamed: text -> body
id, title, body

>> pipeline
Source:
  sample.jsonl
Transforms:
  1. remove unwanted_field
  2. rename text -> body

>> write_jsonl output.jsonl
100

>> save_config pipeline_config.json
Config saved: pipeline_config.json

>> exit
```

### Programmatic Usage

```python
from nlp4j_local_search.cli.data import DataShell

shell = DataShell()
shell.execute("data sample.jsonl")
shell.execute("remove unwanted_field")
output = shell.execute("attrs")
print(output)
```

---

## 2. Search CLI (`nlp4j-local-search`)

### Overview
`nlp4j-local-search` is the command-line interface for indexing, querying, and analytics on local Lucene search engines.

### Running

```bash
nlp4j-local-search --help
```

Or via Python:

```bash
python -m nlp4j_local_search.cli.search.main --help
```
