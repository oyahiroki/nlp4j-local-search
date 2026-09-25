# nlp4j_local_search.cli.data — Interactive Data Shell

`nlp4j-data` is an interactive REPL (Read-Eval-Print Loop) for inspecting,
transforming, and exporting JSONL datasets — no JVM required.

---

## Quick Start

```bash
nlp4j-data
```

Or via Python:

```bash
python -m nlp4j_local_search.cli.data.shell
```

The shell opens with a banner and a `>>` prompt.

---

## Module Structure

```
cli/data/
├── __init__.py    # Package exports: DataShell, DataShellContext, build_default_registry
├── shell.py       # DataShell REPL loop and main() entry point
├── context.py     # DataShellContext — mutable state and undo stack
└── commands.py    # Command implementations (Command Pattern)
```

### `shell.py` — `DataShell`

The main REPL class. Owns a `DataShellContext` and a `CommandRegistry`.

```python
class DataShell:
    def execute(self, line: str) -> str: ...   # parse + dispatch one command
    def run(self) -> None: ...                 # blocking REPL loop (reads stdin)
```

`execute()` is the single entry point for both interactive use and programmatic
driving (e.g. tests).  It tokenises the input with `shlex.split`, looks up the
command in the registry, calls `Command.execute()`, and returns the output string.

### `context.py` — `DataShellContext`

Holds all mutable state shared across commands in a single REPL session.

| Attribute | Type | Description |
|---|---|---|
| `pipeline` | `DataPipeline \| None` | The current pipeline, or `None` before `data` is called. |
| `history` | `list[DataPipeline]` | Undo stack — each pipeline-mutating command pushes the old state here. |

Key methods:

```python
context.push_history()      # snapshot current pipeline onto the undo stack
context.require_pipeline()  # return pipeline or raise CommandError if not loaded
```

`CommandError` is also defined here and raised by any command that detects a
usage or argument error.

### `commands.py` — Command Pattern

Every command is a class with:

| Attribute / Method | Description |
|---|---|
| `name: str` | Keyword the user types. |
| `usage: str` | One-line syntax shown in help. |
| `description: str` | Short description shown in help. |
| `execute(context, args) -> str \| None` | Command logic; returns output or `None`. |

`CommandRegistry` maps names to instances. `build_default_registry()` assembles
the default set at startup.

---

## Commands

| Command | Syntax | Description |
|---|---|---|
| `data` | `data <path>` | Open a JSONL file as the active data source. Clears the undo history. |
| `attrs` | `attrs` | Show field names of the first transformed document. |
| `head` | `head [n]` | Preview the first *n* transformed documents in JSON format (default: 1). |
| `remove` | `remove <field> [field ...]` | Remove one or more fields from every document. Pushes undo state. |
| `rename` | `rename <from> <to>` | Rename a field. Pushes undo state. |
| `pipeline` | `pipeline` | Show the current data source path and the applied transformation chain. |
| `undo` | `undo` | Revert the last transformation step. |
| `write_jsonl` | `write_jsonl <path>` | Write transformed documents to a JSONL file. |
| `save_config` | `save_config <path>` | Save the pipeline definition to a JSON config file. |
| `help` / `?` | `help [command]` | List all commands, or show usage for a specific command. |
| `exit` / `quit` | `exit` | Exit the shell. |

---

## Session Example

```text
nlp4j-data 0.1.0
Type 'help' or '?' for available commands.

>> data sample.jsonl
Loaded source: sample.jsonl
Documents: 100

>> attrs
id
title
text
category
unwanted_field

>> head 1
{"id": "1", "title": "First Document", "text": "Hello world", "category": "tech", "unwanted_field": "temp"}

>> remove unwanted_field
Removed: unwanted_field
id, title, text, category

>> rename text body
Renamed: text -> body
id, title, body, category

>> rename category category_s
Renamed: category -> category_s
id, title, body, category_s

>> pipeline
Source:
  sample.jsonl
Transforms:
  1. remove unwanted_field
  2. rename text -> body
  3. rename category -> category_s

>> undo
Undone. Current attrs: id, title, body, category

>> write_jsonl output.jsonl
100

>> save_config pipeline.json
Config saved: pipeline.json

>> exit
```

---

## Programmatic Usage

`DataShell` can be driven from Python — useful for testing or scripting:

```python
from nlp4j_local_search.cli.data import DataShell

shell = DataShell()
shell.execute("data sample.jsonl")
shell.execute("remove unwanted_field")
shell.execute("rename text body")
output = shell.execute("attrs")
print(output)
# id
# title
# body
# category
```

---

## Relationship to `DataPipeline`

Each pipeline-mutating command wraps a [`DataPipeline`][pipeline] operation.
`DataPipeline` is immutable — every transform returns a new instance.
The context stores the current instance, and `push_history()` saves the
previous one for undo.

```
DataShell.execute("rename text body")
  └─► RenameCommand.execute(context, ["text", "body"])
        ├─► context.push_history()            # save old pipeline
        └─► context.pipeline = pipeline.rename("text", "body")  # new instance
```

`DataPipeline` operations work without a JVM. `load()` (which indexes
documents into a `SearchEngine`) is the only operation that requires one.

[pipeline]: ../../../../data/pipeline.py

---

## Adding a Custom Command

1. Subclass `Command` in `commands.py`.
2. Set `name`, `usage`, `description`.
3. Implement `execute(context, args) -> str | None`.
4. Register it in `build_default_registry()`.

```python
class CountCommand(Command):
    name = "count"
    usage = "count"
    description = "Show the total number of documents."

    def execute(self, context: DataShellContext, args):
        pipeline = context.require_pipeline()
        n = sum(1 for _ in pipeline.iter_documents())
        return str(n)
```
