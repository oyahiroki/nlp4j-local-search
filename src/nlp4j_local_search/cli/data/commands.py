"""CLI commands — Command Pattern implementation for the DataShell REPL.

Each command class:
- declares a ``name`` class attribute (the keyword typed by the user)
- declares a ``usage`` and ``description`` for help text
- implements ``execute(context, args) -> str | None``
  (returns a string to print, or None for no output)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from ...data.pipeline import DataPipeline
from .context import CommandError, DataShellContext


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Command:
    name: str = ""
    usage: str = ""
    description: str = ""

    def execute(
        self,
        context: DataShellContext,
        args: List[str],
    ) -> Optional[str]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# data <path>
# ---------------------------------------------------------------------------

class DataCommand(Command):
    name = "data"
    usage = "data <path>"
    description = "Open a JSONL file as the data source."

    def execute(self, context: DataShellContext, args: List[str]) -> str:
        if len(args) != 1:
            raise CommandError(f"Usage: {self.usage}")
        path = args[0]
        if not Path(path).exists():
            raise CommandError(f"File not found: {path}")
        # Use optional engine from context (None → pure-Python mode, no JVM)
        engine = getattr(context, "engine", None)
        context.history.clear()
        context.pipeline = DataPipeline.from_jsonl(path, engine=engine)
        docs = context.pipeline.head(1)
        count_hint = ""
        if docs:
            # Fast count via streaming iteration (constant memory)
            count = sum(1 for _ in context.pipeline.iter_documents())
            count_hint = f"\nDocuments: {count}"
        return f"Loaded source: {path}{count_hint}"


# ---------------------------------------------------------------------------
# attrs
# ---------------------------------------------------------------------------

class AttrsCommand(Command):
    name = "attrs"
    usage = "attrs"
    description = "Show the field names of the first transformed document."

    def execute(self, context: DataShellContext, args: List[str]) -> str:
        pipeline = context.require_pipeline()
        fields = pipeline.attrs()
        if not fields:
            return "(no documents)"
        return "\n".join(fields)


# ---------------------------------------------------------------------------
# head [n]
# ---------------------------------------------------------------------------

class HeadCommand(Command):
    name = "head"
    usage = "head [n]"
    description = "Show the first n transformed documents (default: 1)."

    def execute(self, context: DataShellContext, args: List[str]) -> str:
        pipeline = context.require_pipeline()
        size = 1
        if args:
            try:
                size = int(args[0])
            except ValueError:
                raise CommandError(f"Usage: {self.usage}")
        docs = pipeline.head(size)
        if not docs:
            return "(no documents)"
        return "\n".join(json.dumps(d, ensure_ascii=False) for d in docs)


# ---------------------------------------------------------------------------
# remove <field> [field ...]
# ---------------------------------------------------------------------------

class RemoveCommand(Command):
    name = "remove"
    usage = "remove <field> [field ...]"
    description = "Remove one or more fields from every document."

    def execute(self, context: DataShellContext, args: List[str]) -> str:
        if not args:
            raise CommandError(f"Usage: {self.usage}")
        context.push_history()
        context.pipeline = context.require_pipeline().remove(*args)
        fields = ", ".join(context.pipeline.attrs())
        return f"Removed: {', '.join(args)}\n{fields}"


# ---------------------------------------------------------------------------
# rename <from> <to>
# ---------------------------------------------------------------------------

class RenameCommand(Command):
    name = "rename"
    usage = "rename <from> <to>"
    description = "Rename a field."

    def execute(self, context: DataShellContext, args: List[str]) -> str:
        if len(args) != 2:
            raise CommandError(f"Usage: {self.usage}")
        source, target = args
        context.push_history()
        context.pipeline = context.require_pipeline().rename(source, target)
        fields = ", ".join(context.pipeline.attrs())
        return f"Renamed: {source} -> {target}\n{fields}"


# ---------------------------------------------------------------------------
# pipeline
# ---------------------------------------------------------------------------

class PipelineCommand(Command):
    name = "pipeline"
    usage = "pipeline"
    description = "Show the current transformation pipeline."

    def execute(self, context: DataShellContext, args: List[str]) -> str:
        pipeline = context.require_pipeline()
        lines = ["Source:", f"  {pipeline.source.path}"]
        transforms = pipeline.transforms
        if transforms:
            lines.append("Transforms:")
            for i, t in enumerate(transforms, start=1):
                cfg = t.to_config()
                t_type = cfg["type"]
                if t_type == "remove":
                    detail = f"remove {', '.join(cfg['fields'])}"
                elif t_type == "rename":
                    detail = f"rename {cfg['source']} -> {cfg['target']}"
                elif t_type == "embedding":
                    detail = f"embedding {cfg['source']} -> {cfg['target']}"
                else:
                    detail = str(cfg)
                lines.append(f"  {i}. {detail}")
        else:
            lines.append("Transforms: (none)")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# undo
# ---------------------------------------------------------------------------

class UndoCommand(Command):
    name = "undo"
    usage = "undo"
    description = "Undo the last transformation."

    def execute(self, context: DataShellContext, args: List[str]) -> str:
        if not context.history:
            raise CommandError("Nothing to undo.")
        context.pipeline = context.history.pop()
        fields = ", ".join(context.pipeline.attrs())
        return f"Undone. Current attrs: {fields}"


# ---------------------------------------------------------------------------
# write_jsonl <path>
# ---------------------------------------------------------------------------

class WriteJsonlCommand(Command):
    name = "write_jsonl"
    usage = "write_jsonl <path>"
    description = "Write transformed documents to a JSONL file."

    def execute(self, context: DataShellContext, args: List[str]) -> str:
        if len(args) != 1:
            raise CommandError(f"Usage: {self.usage}")
        pipeline = context.require_pipeline()
        result = pipeline.write_jsonl(args[0])
        return str(result)


# ---------------------------------------------------------------------------
# save_config <path>
# ---------------------------------------------------------------------------

class SaveConfigCommand(Command):
    name = "save_config"
    usage = "save_config <path>"
    description = "Save the pipeline configuration to a JSON file."

    def execute(self, context: DataShellContext, args: List[str]) -> str:
        if len(args) != 1:
            raise CommandError(f"Usage: {self.usage}")
        context.require_pipeline().save_config(args[0])
        return f"Config saved: {args[0]}"


# ---------------------------------------------------------------------------
# help / ?
# ---------------------------------------------------------------------------

class HelpCommand(Command):
    name = "help"
    usage = "help [command]"
    description = "Show help. Use '?' as an alias."

    def __init__(self, registry: "CommandRegistry"):
        self._registry = registry

    def execute(self, context: DataShellContext, args: List[str]) -> str:
        if args:
            cmd_name = args[0].lstrip("?")
            cmd = self._registry.get(cmd_name)
            if cmd is None:
                raise CommandError(f"Unknown command: {cmd_name}")
            return f"{cmd.usage}\n\n    {cmd.description}"

        lines = ["Commands:", ""]
        for cmd in self._registry.all():
            lines.append(f"  {cmd.usage}")
            lines.append(f"      {cmd.description}")
            lines.append("")
        return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# exit
# ---------------------------------------------------------------------------

class ExitCommand(Command):
    name = "exit"
    usage = "exit"
    description = "Exit the shell."

    def execute(self, context: DataShellContext, args: List[str]) -> Optional[str]:
        raise SystemExit(0)


# ---------------------------------------------------------------------------
# CommandRegistry
# ---------------------------------------------------------------------------

class CommandRegistry:
    """Maps command names to Command instances."""

    def __init__(self) -> None:
        self._commands: dict = {}

    def register(self, cmd: Command) -> None:
        self._commands[cmd.name] = cmd

    def get(self, name: str) -> Optional[Command]:
        return self._commands.get(name)

    def all(self) -> list:
        return list(self._commands.values())


def build_default_registry() -> CommandRegistry:
    """Create and return the default registry with all first-stage commands."""
    registry = CommandRegistry()
    help_cmd = HelpCommand(registry)

    for cmd in [
        DataCommand(),
        AttrsCommand(),
        HeadCommand(),
        RemoveCommand(),
        RenameCommand(),
        PipelineCommand(),
        UndoCommand(),
        WriteJsonlCommand(),
        SaveConfigCommand(),
        help_cmd,
        ExitCommand(),
    ]:
        registry.register(cmd)

    # aliases
    registry._commands["?"] = help_cmd
    registry._commands["quit"] = ExitCommand()

    return registry
