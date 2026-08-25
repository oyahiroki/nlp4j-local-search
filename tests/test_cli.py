"""
Tests for the nlp4j_local_search.cli subpackage and
DataPipeline inspection API (attrs / head).

All tests run without a JVM — no SearchEngine, no Lucene, no OpenNLP.
The _NoEngine stub inside commands.py is used for JSONL-only workflows.
"""
from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from nlp4j_local_search.cli import CommandError, DataShell, DataShellContext
from nlp4j_local_search.cli.commands import (
    AttrsCommand,
    DataCommand,
    HeadCommand,
    HelpCommand,
    PipelineCommand,
    RemoveCommand,
    RenameCommand,
    SaveConfigCommand,
    UndoCommand,
    WriteJsonlCommand,
    build_default_registry,
)
from nlp4j_local_search.data import DataPipeline, JsonlSource


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_DOCS = [
    {"id": 1, "category": "city",    "text": "this is test 1.", "xxx": "aaa"},
    {"id": 2, "category": "company", "text": "this is test 2.", "xxx": "aaa"},
    {"id": 3, "category": "city",    "text": "this is test 3.", "xxx": "aaa"},
]


def _make_jsonl(tmp_path: Path, docs: list) -> Path:
    p = tmp_path / "input.jsonl"
    with open(p, "w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    return p


class FakeEngine:
    """Minimal stub — no JVM needed."""
    docs: list
    committed: int
    embedding = None

    def __init__(self):
        self.docs = []
        self.committed = 0

    def add_json(self, doc: dict) -> None:
        self.docs.append(doc)

    def commit(self) -> None:
        self.committed += 1


def _pipeline(tmp_path, docs=None) -> DataPipeline:
    """Return a fresh DataPipeline backed by a FakeEngine."""
    p = _make_jsonl(tmp_path, SAMPLE_DOCS if docs is None else docs)
    return DataPipeline.from_jsonl(p, engine=FakeEngine())


# ===========================================================================
# DataPipeline.attrs()
# ===========================================================================

class TestAttrs:
    def test_returns_field_names(self, tmp_path):
        pipeline = _pipeline(tmp_path)
        assert pipeline.attrs() == ["id", "category", "text", "xxx"]

    def test_after_remove(self, tmp_path):
        pipeline = _pipeline(tmp_path).remove("xxx")
        assert pipeline.attrs() == ["id", "category", "text"]

    def test_after_rename(self, tmp_path):
        pipeline = _pipeline(tmp_path).rename("text", "text_en")
        assert "text_en" in pipeline.attrs()
        assert "text" not in pipeline.attrs()

    def test_empty_source(self, tmp_path):
        pipeline = _pipeline(tmp_path, [])
        assert pipeline.attrs() == []

    def test_does_not_call_engine(self, tmp_path):
        engine = FakeEngine()
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        pipeline = DataPipeline.from_jsonl(p, engine=engine)
        pipeline.attrs()
        assert engine.committed == 0


# ===========================================================================
# DataPipeline.head()
# ===========================================================================

class TestHead:
    def test_returns_list_of_dicts(self, tmp_path):
        pipeline = _pipeline(tmp_path)
        result = pipeline.head()
        assert isinstance(result, list)
        assert all(isinstance(d, dict) for d in result)

    def test_default_size_1(self, tmp_path):
        pipeline = _pipeline(tmp_path)
        assert len(pipeline.head()) == 1

    def test_custom_size(self, tmp_path):
        pipeline = _pipeline(tmp_path)
        assert len(pipeline.head(2)) == 2

    def test_size_larger_than_source(self, tmp_path):
        pipeline = _pipeline(tmp_path)
        assert len(pipeline.head(100)) == 3

    def test_transforms_applied(self, tmp_path):
        pipeline = _pipeline(tmp_path).remove("xxx").rename("text", "text_en")
        doc = pipeline.head(1)[0]
        assert "xxx" not in doc
        assert "text_en" in doc

    def test_empty_source(self, tmp_path):
        pipeline = _pipeline(tmp_path, [])
        assert pipeline.head() == []

    def test_does_not_call_engine(self, tmp_path):
        engine = FakeEngine()
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        pipeline = DataPipeline.from_jsonl(p, engine=engine)
        pipeline.head(3)
        assert engine.committed == 0


# ===========================================================================
# DataShellContext
# ===========================================================================

class TestDataShellContext:
    def test_require_pipeline_raises_when_none(self):
        ctx = DataShellContext()
        with pytest.raises(CommandError, match="No data source"):
            ctx.require_pipeline()

    def test_require_pipeline_returns_pipeline(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path)
        assert ctx.require_pipeline() is ctx.pipeline

    def test_push_history(self, tmp_path):
        ctx = DataShellContext()
        p1 = _pipeline(tmp_path)
        ctx.pipeline = p1
        ctx.push_history()
        assert ctx.history == [p1]

    def test_push_history_noop_when_pipeline_none(self):
        ctx = DataShellContext()
        ctx.push_history()
        assert ctx.history == []


# ===========================================================================
# DataCommand
# ===========================================================================

class TestDataCommand:
    def test_loads_source(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        ctx = DataShellContext()
        cmd = DataCommand()
        output = cmd.execute(ctx, [str(p)])
        assert ctx.pipeline is not None
        assert "Loaded source" in output

    def test_reports_document_count(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        ctx = DataShellContext()
        cmd = DataCommand()
        output = cmd.execute(ctx, [str(p)])
        assert "3" in output

    def test_clears_history(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        ctx = DataShellContext()
        ctx.history.append("old_pipeline_stub")
        cmd = DataCommand()
        cmd.execute(ctx, [str(p)])
        assert ctx.history == []

    def test_file_not_found_raises(self, tmp_path):
        ctx = DataShellContext()
        cmd = DataCommand()
        with pytest.raises(CommandError, match="File not found"):
            cmd.execute(ctx, ["nonexistent.jsonl"])

    def test_missing_arg_raises(self):
        ctx = DataShellContext()
        cmd = DataCommand()
        with pytest.raises(CommandError, match="Usage"):
            cmd.execute(ctx, [])


# ===========================================================================
# AttrsCommand
# ===========================================================================

class TestAttrsCommand:
    def test_shows_fields(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path)
        output = AttrsCommand().execute(ctx, [])
        for field in ["id", "category", "text", "xxx"]:
            assert field in output

    def test_after_remove(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path).remove("xxx")
        output = AttrsCommand().execute(ctx, [])
        assert "xxx" not in output

    def test_no_pipeline_raises(self):
        ctx = DataShellContext()
        with pytest.raises(CommandError):
            AttrsCommand().execute(ctx, [])


# ===========================================================================
# HeadCommand
# ===========================================================================

class TestHeadCommand:
    def test_default_shows_one_doc(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path)
        output = HeadCommand().execute(ctx, [])
        lines = [l for l in output.splitlines() if l.strip()]
        assert len(lines) == 1

    def test_custom_size(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path)
        output = HeadCommand().execute(ctx, ["2"])
        lines = [l for l in output.splitlines() if l.strip()]
        assert len(lines) == 2

    def test_invalid_size_raises(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path)
        with pytest.raises(CommandError):
            HeadCommand().execute(ctx, ["notanumber"])

    def test_no_pipeline_raises(self):
        ctx = DataShellContext()
        with pytest.raises(CommandError):
            HeadCommand().execute(ctx, [])


# ===========================================================================
# RemoveCommand
# ===========================================================================

class TestRemoveCommand:
    def test_removes_field(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path)
        RemoveCommand().execute(ctx, ["xxx"])
        assert "xxx" not in ctx.pipeline.attrs()

    def test_pushes_history(self, tmp_path):
        ctx = DataShellContext()
        original = _pipeline(tmp_path)
        ctx.pipeline = original
        RemoveCommand().execute(ctx, ["xxx"])
        assert ctx.history == [original]

    def test_output_shows_remaining_fields(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path)
        output = RemoveCommand().execute(ctx, ["xxx"])
        assert "xxx" not in output.split("\n")[-1]

    def test_missing_arg_raises(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path)
        with pytest.raises(CommandError):
            RemoveCommand().execute(ctx, [])

    def test_no_pipeline_raises(self):
        ctx = DataShellContext()
        with pytest.raises(CommandError):
            RemoveCommand().execute(ctx, ["xxx"])


# ===========================================================================
# RenameCommand
# ===========================================================================

class TestRenameCommand:
    def test_renames_field(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path)
        RenameCommand().execute(ctx, ["text", "text_en"])
        attrs = ctx.pipeline.attrs()
        assert "text_en" in attrs
        assert "text" not in attrs

    def test_pushes_history(self, tmp_path):
        ctx = DataShellContext()
        original = _pipeline(tmp_path)
        ctx.pipeline = original
        RenameCommand().execute(ctx, ["text", "text_en"])
        assert ctx.history == [original]

    def test_output_shows_new_name(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path)
        output = RenameCommand().execute(ctx, ["text", "text_en"])
        assert "text_en" in output

    def test_wrong_arg_count_raises(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path)
        with pytest.raises(CommandError, match="Usage"):
            RenameCommand().execute(ctx, ["only_one"])

    def test_no_pipeline_raises(self):
        ctx = DataShellContext()
        with pytest.raises(CommandError):
            RenameCommand().execute(ctx, ["text", "text_en"])


# ===========================================================================
# PipelineCommand
# ===========================================================================

class TestPipelineCommand:
    def test_shows_source_path(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        ctx = DataShellContext()
        ctx.pipeline = DataPipeline.from_jsonl(p, engine=FakeEngine())
        output = PipelineCommand().execute(ctx, [])
        assert str(p) in output

    def test_shows_transforms(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path).remove("xxx").rename("text", "text_en")
        output = PipelineCommand().execute(ctx, [])
        assert "remove" in output
        assert "rename" in output

    def test_no_pipeline_raises(self):
        ctx = DataShellContext()
        with pytest.raises(CommandError):
            PipelineCommand().execute(ctx, [])


# ===========================================================================
# UndoCommand
# ===========================================================================

class TestUndoCommand:
    def test_restores_previous_pipeline(self, tmp_path):
        ctx = DataShellContext()
        original = _pipeline(tmp_path)
        ctx.pipeline = original
        ctx.push_history()
        ctx.pipeline = original.remove("xxx")
        UndoCommand().execute(ctx, [])
        assert ctx.pipeline is original

    def test_pops_history(self, tmp_path):
        ctx = DataShellContext()
        original = _pipeline(tmp_path)
        ctx.pipeline = original
        ctx.push_history()
        ctx.pipeline = original.remove("xxx")
        UndoCommand().execute(ctx, [])
        assert ctx.history == []

    def test_nothing_to_undo_raises(self):
        ctx = DataShellContext()
        ctx.pipeline = None
        with pytest.raises(CommandError, match="Nothing to undo"):
            UndoCommand().execute(ctx, [])


# ===========================================================================
# WriteJsonlCommand
# ===========================================================================

class TestWriteJsonlCommand:
    def test_writes_file(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path)
        out = tmp_path / "out.jsonl"
        WriteJsonlCommand().execute(ctx, [str(out)])
        assert out.exists()

    def test_count_in_output(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path)
        out = tmp_path / "out.jsonl"
        output = WriteJsonlCommand().execute(ctx, [str(out)])
        assert "3" in output

    def test_transforms_applied_in_output(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path).remove("xxx")
        out = tmp_path / "out.jsonl"
        WriteJsonlCommand().execute(ctx, [str(out)])
        for doc in JsonlSource(out):
            assert "xxx" not in doc

    def test_missing_arg_raises(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path)
        with pytest.raises(CommandError, match="Usage"):
            WriteJsonlCommand().execute(ctx, [])

    def test_no_pipeline_raises(self):
        ctx = DataShellContext()
        with pytest.raises(CommandError):
            WriteJsonlCommand().execute(ctx, ["out.jsonl"])


# ===========================================================================
# SaveConfigCommand
# ===========================================================================

class TestSaveConfigCommand:
    def test_writes_config_file(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path).remove("xxx")
        cfg = tmp_path / "cfg.json"
        SaveConfigCommand().execute(ctx, [str(cfg)])
        assert cfg.exists()

    def test_config_is_valid_json(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path).remove("xxx")
        cfg = tmp_path / "cfg.json"
        SaveConfigCommand().execute(ctx, [str(cfg)])
        loaded = json.loads(cfg.read_text(encoding="utf-8"))
        assert loaded["version"] == 1

    def test_missing_arg_raises(self, tmp_path):
        ctx = DataShellContext()
        ctx.pipeline = _pipeline(tmp_path)
        with pytest.raises(CommandError, match="Usage"):
            SaveConfigCommand().execute(ctx, [])


# ===========================================================================
# HelpCommand
# ===========================================================================

class TestHelpCommand:
    def test_lists_all_commands(self):
        registry = build_default_registry()
        help_cmd = HelpCommand(registry)
        ctx = DataShellContext()
        output = help_cmd.execute(ctx, [])
        for name in ["data", "attrs", "head", "remove", "rename",
                     "pipeline", "undo", "write_jsonl", "help", "exit"]:
            assert name in output

    def test_help_for_specific_command(self):
        registry = build_default_registry()
        help_cmd = HelpCommand(registry)
        ctx = DataShellContext()
        output = help_cmd.execute(ctx, ["rename"])
        assert "rename" in output

    def test_unknown_command_raises(self):
        registry = build_default_registry()
        help_cmd = HelpCommand(registry)
        ctx = DataShellContext()
        with pytest.raises(CommandError, match="Unknown command"):
            help_cmd.execute(ctx, ["nonexistent"])


# ===========================================================================
# DataShell.execute() — integration via the shell dispatcher
# ===========================================================================

class TestDataShellExecute:
    def test_empty_line_is_noop(self):
        shell = DataShell()
        assert shell.execute("") == ""

    def test_comment_is_noop(self):
        shell = DataShell()
        assert shell.execute("# comment") == ""

    def test_unknown_command_raises(self):
        shell = DataShell()
        with pytest.raises(CommandError, match="Unknown command"):
            shell.execute("bogus_cmd")

    def test_full_workflow(self, tmp_path):
        """data → remove → rename → attrs → head → write_jsonl via shell dispatcher."""
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        out = tmp_path / "out.jsonl"

        shell = DataShell()
        shell.execute(f"data {shlex.quote(str(p))}")
        shell.execute("remove xxx")
        shell.execute("rename text text_en")

        attrs_output = shell.execute("attrs")
        assert "text_en" in attrs_output
        assert "xxx" not in attrs_output

        head_output = shell.execute("head 1")
        doc = json.loads(head_output.strip().splitlines()[0])
        assert "text_en" in doc
        assert "xxx" not in doc

        shell.execute(f"write_jsonl {shlex.quote(str(out))}")
        written = list(JsonlSource(out))
        assert len(written) == 3
        assert all("xxx" not in d for d in written)

    def test_undo_via_shell(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        shell = DataShell()
        shell.execute(f"data {shlex.quote(str(p))}")
        shell.execute("remove xxx")

        assert "xxx" not in shell.execute("attrs")

        shell.execute("undo")
        attrs_after_undo = shell.execute("attrs")
        assert "xxx" in attrs_after_undo

    def test_pipeline_command_via_shell(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        shell = DataShell()
        shell.execute(f"data {shlex.quote(str(p))}")
        shell.execute("remove xxx")
        shell.execute("rename text text_en")
        output = shell.execute("pipeline")
        assert "remove" in output
        assert "rename" in output

    def test_save_config_via_shell(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        cfg = tmp_path / "cfg.json"
        shell = DataShell()
        shell.execute(f"data {shlex.quote(str(p))}")
        shell.execute("remove xxx")
        shell.execute(f"save_config {shlex.quote(str(cfg))}")
        assert cfg.exists()

    def test_question_mark_alias(self):
        shell = DataShell()
        output = shell.execute("?")
        assert "Commands" in output

    def test_quoted_field_names(self, tmp_path):
        """shlex should handle quoted field names with spaces."""
        docs = [{"id": 1, "original text": "hello"}]
        p = _make_jsonl(tmp_path, docs)
        shell = DataShell()
        shell.execute(f"data {shlex.quote(str(p))}")
        shell.execute('rename "original text" text_en')
        attrs = shell.execute("attrs")
        assert "text_en" in attrs
        assert "original text" not in attrs
