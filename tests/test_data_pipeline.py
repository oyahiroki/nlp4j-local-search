"""
Tests for the nlp4j_local_search.data subpackage.

All tests run without a JVM — SearchEngine is stubbed out via a minimal
FakeEngine that records calls to add_json() and commit().
"""
from __future__ import annotations

import json
import os
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from nlp4j_local_search.data import (
    DataPipeline,
    DataPipelineError,
    EmbeddingTransform,
    JsonlSink,
    JsonlSource,
    LoadResult,
    PipelineConfig,
    RemoveTransform,
    RenameTransform,
    WriteResult,
)
from nlp4j_local_search import data as data_func


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jsonl(tmp_path: Path, docs: list) -> Path:
    """Write *docs* as JSONL to a temp file and return the Path."""
    p = tmp_path / "input.jsonl"
    with open(p, "w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    return p


SAMPLE_DOCS = [
    {"id": 1, "category": "city",    "text": "this is test 1.", "xxx": "aaa"},
    {"id": 2, "category": "company", "text": "this is test 2.", "xxx": "aaa"},
    {"id": 3, "category": "city",    "text": "this is test 3.", "xxx": "aaa"},
]


class FakeEngine:
    """Minimal stub — records add_json / commit calls; no JVM needed."""

    def __init__(self):
        self.docs: list = []
        self.committed: int = 0
        self.embedding = None  # can be replaced per test

    def add_json(self, doc: dict) -> None:
        self.docs.append(doc)

    def commit(self) -> None:
        self.committed += 1


class DummyEmbeddingProvider:
    """Deterministic 2-D provider — no model loading."""

    @property
    def dimension(self) -> int:
        return 2

    def embed_query(self, text: str):
        return [0.0, 1.0]

    def embed_documents(self, texts):
        return [[float(i % 10) / 10, 1.0] for i, _ in enumerate(texts)]


# ===========================================================================
# RemoveTransform
# ===========================================================================

class TestRemoveTransform:
    def test_removes_specified_field(self):
        t = RemoveTransform(("xxx",))
        result = t.apply({"id": 1, "xxx": "aaa", "text": "hello"})
        assert result == {"id": 1, "text": "hello"}

    def test_removes_multiple_fields(self):
        t = RemoveTransform(("a", "b"))
        result = t.apply({"id": 1, "a": 1, "b": 2, "c": 3})
        assert result == {"id": 1, "c": 3}

    def test_missing_field_is_noop(self):
        t = RemoveTransform(("nonexistent",))
        doc = {"id": 1, "text": "hello"}
        result = t.apply(doc)
        assert result == doc

    def test_does_not_mutate_original(self):
        t = RemoveTransform(("xxx",))
        original = {"id": 1, "xxx": "aaa"}
        t.apply(original)
        assert "xxx" in original

    def test_to_config(self):
        t = RemoveTransform(("a", "b"))
        config = t.to_config()
        assert config == {"type": "remove", "fields": ["a", "b"]}


# ===========================================================================
# RenameTransform
# ===========================================================================

class TestRenameTransform:
    def test_renames_field(self):
        t = RenameTransform("category", "category_s")
        result = t.apply({"id": 1, "category": "city"})
        assert result == {"id": 1, "category_s": "city"}

    def test_source_absent_is_noop(self):
        t = RenameTransform("missing", "new")
        doc = {"id": 1, "text": "hello"}
        result = t.apply(doc)
        assert result == doc

    def test_does_not_mutate_original(self):
        t = RenameTransform("category", "category_s")
        original = {"id": 1, "category": "city"}
        t.apply(original)
        assert "category" in original

    def test_to_config(self):
        t = RenameTransform("text", "text_en")
        config = t.to_config()
        assert config == {"type": "rename", "source": "text", "target": "text_en"}


# ===========================================================================
# EmbeddingTransform
# ===========================================================================

class TestEmbeddingTransform:
    def test_apply_batch_adds_vector_field(self):
        t = EmbeddingTransform(source="text", target="vector")
        provider = DummyEmbeddingProvider()
        docs = [{"id": 1, "text": "hello"}, {"id": 2, "text": "world"}]
        result = t.apply_batch(docs, provider)
        assert all("vector" in d for d in result)

    def test_apply_batch_vector_length(self):
        t = EmbeddingTransform(source="text", target="vector")
        provider = DummyEmbeddingProvider()
        docs = [{"id": i, "text": f"text {i}"} for i in range(5)]
        result = t.apply_batch(docs, provider)
        assert all(len(d["vector"]) == provider.dimension for d in result)

    def test_apply_batch_preserves_original_fields(self):
        t = EmbeddingTransform(source="text", target="vector")
        provider = DummyEmbeddingProvider()
        docs = [{"id": 1, "text": "hello", "category": "city"}]
        result = t.apply_batch(docs, provider)
        assert result[0]["id"] == 1
        assert result[0]["category"] == "city"

    def test_apply_batch_does_not_mutate_original(self):
        t = EmbeddingTransform(source="text", target="vector")
        provider = DummyEmbeddingProvider()
        original = [{"id": 1, "text": "hello"}]
        t.apply_batch(original, provider)
        assert "vector" not in original[0]

    def test_apply_raises_not_implemented(self):
        t = EmbeddingTransform(source="text")
        with pytest.raises(NotImplementedError):
            t.apply({"id": 1})

    def test_to_config_defaults(self):
        t = EmbeddingTransform(source="text_en")
        config = t.to_config()
        assert config["type"] == "embedding"
        assert config["source"] == "text_en"
        assert config["target"] == "vector"

    def test_to_config_custom_target(self):
        t = EmbeddingTransform(source="title", target="title_vector")
        config = t.to_config()
        assert config["target"] == "title_vector"


# ===========================================================================
# JsonlSource
# ===========================================================================

class TestJsonlSource:
    def test_iterates_all_docs(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        docs = list(JsonlSource(p))
        assert len(docs) == 3

    def test_skips_empty_lines(self, tmp_path):
        p = tmp_path / "input.jsonl"
        p.write_text(
            '{"id":1}\n\n{"id":2}\n\n',
            encoding="utf-8",
        )
        docs = list(JsonlSource(p))
        assert len(docs) == 2

    def test_correct_values(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        docs = list(JsonlSource(p))
        assert docs[0]["id"] == 1
        assert docs[1]["category"] == "company"

    def test_to_config(self, tmp_path):
        p = tmp_path / "data.jsonl"
        s = JsonlSource(p)
        config = s.to_config()
        assert config["type"] == "jsonl"
        assert config["path"] == str(p)


# ===========================================================================
# JsonlSink
# ===========================================================================

class TestJsonlSink:
    def test_writes_docs(self, tmp_path):
        p = tmp_path / "out.jsonl"
        with JsonlSink(p) as sink:
            sink.write({"id": 1, "text": "hello"})
            sink.write({"id": 2, "text": "world"})
        lines = p.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0]) == {"id": 1, "text": "hello"}

    def test_write_outside_context_raises(self, tmp_path):
        sink = JsonlSink(tmp_path / "out.jsonl")
        with pytest.raises(RuntimeError):
            sink.write({"id": 1})

    def test_unicode_preserved(self, tmp_path):
        p = tmp_path / "out.jsonl"
        with JsonlSink(p) as sink:
            sink.write({"text": "日本語テスト"})
        content = p.read_text(encoding="utf-8")
        assert "日本語テスト" in content


# ===========================================================================
# DataPipeline — immutability
# ===========================================================================

class TestDataPipelineImmutability:
    def _base(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        return DataPipeline.from_jsonl(p, engine=engine)

    def test_from_jsonl_creates_pipeline(self, tmp_path):
        pipeline = self._base(tmp_path)
        assert isinstance(pipeline, DataPipeline)

    def test_remove_returns_new_instance(self, tmp_path):
        base = self._base(tmp_path)
        modified = base.remove("xxx")
        assert modified is not base

    def test_remove_does_not_change_original(self, tmp_path):
        base = self._base(tmp_path)
        base.remove("xxx")
        assert len(base.transforms) == 0

    def test_rename_returns_new_instance(self, tmp_path):
        base = self._base(tmp_path)
        modified = base.rename("category", "category_s")
        assert modified is not base

    def test_chained_transforms_accumulate(self, tmp_path):
        base = self._base(tmp_path)
        p2 = base.remove("xxx").rename("category", "category_s")
        assert len(p2.transforms) == 2

    def test_save_as_sets_output_path(self, tmp_path):
        base = self._base(tmp_path)
        p2 = base.save_as("out.jsonl")
        assert p2.output_path == Path("out.jsonl")
        assert base.output_path is None

    def test_save_config_sets_config_path(self, tmp_path):
        base = self._base(tmp_path)
        p2 = base.save_config("settings.json")
        assert p2.config_path == Path("settings.json")
        assert base.config_path is None


# ===========================================================================
# DataPipeline — load() without embedding
# ===========================================================================

class TestDataPipelineLoad:
    def test_load_returns_load_result(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        result = DataPipeline.from_jsonl(p, engine=engine).load()
        assert isinstance(result, LoadResult)

    def test_load_count(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        result = DataPipeline.from_jsonl(p, engine=engine).load()
        assert result.loaded_count == 3
        assert result.read_count == 3

    def test_commit_called_once(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        DataPipeline.from_jsonl(p, engine=engine).load()
        assert engine.committed == 1

    def test_remove_transform_applied(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        DataPipeline.from_jsonl(p, engine=engine).remove("xxx").load()
        for doc in engine.docs:
            assert "xxx" not in doc

    def test_rename_transform_applied(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        DataPipeline.from_jsonl(p, engine=engine) \
            .rename("category", "category_s").load()
        for doc in engine.docs:
            assert "category_s" in doc
            assert "category" not in doc

    def test_remove_and_rename_chained(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        DataPipeline.from_jsonl(p, engine=engine) \
            .remove("xxx") \
            .rename("category", "category_s") \
            .rename("text", "text_en") \
            .load()
        for doc in engine.docs:
            assert "xxx" not in doc
            assert "category_s" in doc
            assert "text_en" in doc

    def test_save_as_writes_jsonl(self, tmp_path):
        input_p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        output_p = tmp_path / "out.jsonl"
        engine = FakeEngine()
        result = (
            DataPipeline.from_jsonl(input_p, engine=engine)
            .remove("xxx")
            .save_as(output_p)
            .load()
        )
        assert result.written_count == 3
        written = list(JsonlSource(output_p))
        assert len(written) == 3
        for doc in written:
            assert "xxx" not in doc

    def test_save_config_writes_json(self, tmp_path):
        input_p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        config_p = tmp_path / "settings.json"
        engine = FakeEngine()
        (
            DataPipeline.from_jsonl(input_p, engine=engine)
            .remove("xxx")
            .rename("text", "text_en")
            .save_config(config_p)
            .load()
        )
        config = json.loads(config_p.read_text(encoding="utf-8"))
        assert config["version"] == 1
        assert config["source"]["type"] == "jsonl"
        transforms = config["transforms"]
        assert transforms[0] == {"type": "remove", "fields": ["xxx"]}
        assert transforms[1] == {"type": "rename", "source": "text", "target": "text_en"}

    def test_load_result_str(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        result = DataPipeline.from_jsonl(p, engine=engine).load()
        s = str(result)
        assert "3" in s
        assert "seconds" in s

    def test_elapsed_seconds_positive(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        result = DataPipeline.from_jsonl(p, engine=engine).load()
        assert result.elapsed_seconds >= 0


# ===========================================================================
# DataPipeline — load() with embedding
# ===========================================================================

class TestDataPipelineEmbedding:
    def test_embedding_adds_vector_field(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        engine.embedding = DummyEmbeddingProvider()
        DataPipeline.from_jsonl(p, engine=engine).embedding("text").load()
        for doc in engine.docs:
            assert "vector" in doc
            assert len(doc["vector"]) == 2

    def test_embedding_with_custom_target(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        engine.embedding = DummyEmbeddingProvider()
        DataPipeline.from_jsonl(p, engine=engine) \
            .embedding("text", "my_vector").load()
        for doc in engine.docs:
            assert "my_vector" in doc

    def test_embedding_without_provider_raises(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()  # embedding is None
        with pytest.raises(DataPipelineError, match="Embedding provider is required"):
            DataPipeline.from_jsonl(p, engine=engine).embedding("text").load()

    def test_full_pipeline(self, tmp_path):
        """End-to-end: remove + rename + rename + embedding + save_as + save_config."""
        input_p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        output_p = tmp_path / "out.jsonl"
        config_p = tmp_path / "settings.json"
        engine = FakeEngine()
        engine.embedding = DummyEmbeddingProvider()

        result = (
            DataPipeline.from_jsonl(input_p, engine=engine)
            .remove("xxx")
            .rename("category", "category_s")
            .rename("text", "text_en")
            .embedding("text_en")
            .save_as(output_p)
            .save_config(config_p)
            .load()
        )

        assert result.loaded_count == 3
        assert result.written_count == 3

        # Verify indexed docs
        for doc in engine.docs:
            assert "xxx" not in doc
            assert "category_s" in doc
            assert "text_en" in doc
            assert "vector" in doc

        # Verify output JSONL
        written = list(JsonlSource(output_p))
        assert len(written) == 3
        assert "vector" in written[0]

        # Verify config
        config = json.loads(config_p.read_text(encoding="utf-8"))
        assert any(t["type"] == "embedding" for t in config["transforms"])


# ===========================================================================
# PipelineConfig
# ===========================================================================

class TestPipelineConfig:
    def test_from_pipeline_version(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        pipeline = (
            DataPipeline.from_jsonl(p, engine=engine)
            .remove("xxx")
        )
        config = PipelineConfig.from_pipeline(pipeline)
        assert config["version"] == 1

    def test_from_pipeline_source(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        pipeline = DataPipeline.from_jsonl(p, engine=engine)
        config = PipelineConfig.from_pipeline(pipeline)
        assert config["source"]["type"] == "jsonl"

    def test_from_pipeline_no_output_key_when_no_save_as(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        pipeline = DataPipeline.from_jsonl(p, engine=engine)
        config = PipelineConfig.from_pipeline(pipeline)
        assert "output" not in config

    def test_from_pipeline_output_key_when_save_as(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        pipeline = DataPipeline.from_jsonl(p, engine=engine).save_as("out.jsonl")
        config = PipelineConfig.from_pipeline(pipeline)
        assert config["output"]["path"] == "out.jsonl"

    def test_save_writes_valid_json(self, tmp_path):
        input_p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        config_p = tmp_path / "cfg.json"
        engine = FakeEngine()
        pipeline = (
            DataPipeline.from_jsonl(input_p, engine=engine)
            .remove("xxx")
            .rename("text", "text_en")
        )
        PipelineConfig.save(pipeline, config_p)
        loaded = json.loads(config_p.read_text(encoding="utf-8"))
        assert loaded["version"] == 1
        assert len(loaded["transforms"]) == 2


# ===========================================================================
# LoadResult
# ===========================================================================

class TestLoadResult:
    def test_str_contains_count(self):
        r = LoadResult(
            read_count=5, loaded_count=5, written_count=0,
            elapsed_seconds=1.23, output_path=None,
        )
        assert "5" in str(r)

    def test_str_contains_seconds(self):
        r = LoadResult(
            read_count=5, loaded_count=5, written_count=0,
            elapsed_seconds=1.23, output_path=None,
        )
        assert "seconds" in str(r).lower()

    def test_repr_equals_str(self):
        r = LoadResult(
            read_count=3, loaded_count=3, written_count=3,
            elapsed_seconds=0.05, output_path=Path("out.jsonl"),
        )
        assert repr(r) == str(r)

    def test_immutable(self):
        r = LoadResult(
            read_count=1, loaded_count=1, written_count=0,
            elapsed_seconds=0.0, output_path=None,
        )
        with pytest.raises((AttributeError, TypeError)):
            r.loaded_count = 99


# ===========================================================================
# WriteResult
# ===========================================================================

class TestWriteResult:
    def test_str_contains_count(self):
        r = WriteResult(path="out.jsonl", count=5, elapsed_seconds=0.12)
        assert "5" in str(r)

    def test_str_contains_path(self):
        r = WriteResult(path="out.jsonl", count=5, elapsed_seconds=0.12)
        assert "out.jsonl" in str(r)

    def test_str_contains_seconds(self):
        r = WriteResult(path="out.jsonl", count=5, elapsed_seconds=0.12)
        assert "seconds" in str(r).lower()

    def test_repr_equals_str(self):
        r = WriteResult(path="out.jsonl", count=3, elapsed_seconds=0.01)
        assert repr(r) == str(r)

    def test_immutable(self):
        r = WriteResult(path="out.jsonl", count=3, elapsed_seconds=0.01)
        with pytest.raises((AttributeError, TypeError)):
            r.count = 99


# ===========================================================================
# DataPipeline.write_jsonl()
# ===========================================================================

class TestWriteJsonl:
    def test_returns_write_result(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        result = DataPipeline.from_jsonl(p, engine=engine).write_jsonl(tmp_path / "out.jsonl")
        assert isinstance(result, WriteResult)

    def test_count(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        result = DataPipeline.from_jsonl(p, engine=engine).write_jsonl(tmp_path / "out.jsonl")
        assert result.count == 3

    def test_path_in_result(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        out = tmp_path / "out.jsonl"
        result = DataPipeline.from_jsonl(p, engine=engine).write_jsonl(out)
        assert result.path == str(out)

    def test_elapsed_seconds_positive(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        result = DataPipeline.from_jsonl(p, engine=engine).write_jsonl(tmp_path / "out.jsonl")
        assert result.elapsed_seconds >= 0

    def test_file_is_created(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        out = tmp_path / "out.jsonl"
        DataPipeline.from_jsonl(p, engine=engine).write_jsonl(out)
        assert out.exists()

    def test_file_line_count(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        out = tmp_path / "out.jsonl"
        DataPipeline.from_jsonl(p, engine=engine).write_jsonl(out)
        lines = [l for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 3

    def test_transforms_applied(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        out = tmp_path / "out.jsonl"
        DataPipeline.from_jsonl(p, engine=engine) \
            .remove("xxx") \
            .rename("category", "category_s") \
            .write_jsonl(out)
        written = list(JsonlSource(out))
        for doc in written:
            assert "xxx" not in doc
            assert "category_s" in doc

    def test_unicode_preserved(self, tmp_path):
        docs = [{"id": 1, "text": "日本語テスト"}]
        p = _make_jsonl(tmp_path, docs)
        engine = FakeEngine()
        out = tmp_path / "out.jsonl"
        DataPipeline.from_jsonl(p, engine=engine).write_jsonl(out)
        content = out.read_text(encoding="utf-8")
        assert "日本語テスト" in content

    def test_does_not_call_engine(self, tmp_path):
        """write_jsonl must not touch the SearchEngine at all."""
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        DataPipeline.from_jsonl(p, engine=engine).write_jsonl(tmp_path / "out.jsonl")
        assert len(engine.docs) == 0
        assert engine.committed == 0

    def test_with_embedding(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        engine.embedding = DummyEmbeddingProvider()
        out = tmp_path / "out.jsonl"
        DataPipeline.from_jsonl(p, engine=engine) \
            .embedding("text") \
            .write_jsonl(out)
        written = list(JsonlSource(out))
        for doc in written:
            assert "vector" in doc

    def test_embedding_without_provider_raises(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()  # embedding is None
        with pytest.raises(DataPipelineError, match="Embedding provider is required"):
            DataPipeline.from_jsonl(p, engine=engine) \
                .embedding("text") \
                .write_jsonl(tmp_path / "out.jsonl")


# ===========================================================================
# DataPipeline.iter_documents() / __iter__
# ===========================================================================

class TestIterDocuments:
    def test_iter_documents_yields_dicts(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        docs = list(DataPipeline.from_jsonl(p, engine=engine).iter_documents())
        assert all(isinstance(d, dict) for d in docs)

    def test_iter_documents_count(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        docs = list(DataPipeline.from_jsonl(p, engine=engine).iter_documents())
        assert len(docs) == 3

    def test_iter_documents_transforms_applied(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        docs = list(
            DataPipeline.from_jsonl(p, engine=engine)
            .remove("xxx")
            .rename("category", "category_s")
            .iter_documents()
        )
        for doc in docs:
            assert "xxx" not in doc
            assert "category_s" in doc

    def test_dunder_iter(self, tmp_path):
        """__iter__ must behave identically to iter_documents()."""
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        pipeline = DataPipeline.from_jsonl(p, engine=engine).remove("xxx")
        docs = list(pipeline)
        assert len(docs) == 3
        for doc in docs:
            assert "xxx" not in doc

    def test_list_conversion(self, tmp_path):
        """list(pipeline) must produce the same result as list(pipeline.iter_documents())."""
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        pipeline = DataPipeline.from_jsonl(p, engine=engine).rename("category", "cat")
        assert list(pipeline) == list(pipeline.iter_documents())

    def test_iter_does_not_call_engine(self, tmp_path):
        """Iterating must not call add_json or commit."""
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        _ = list(DataPipeline.from_jsonl(p, engine=engine).iter_documents())
        assert len(engine.docs) == 0
        assert engine.committed == 0

    def test_iter_with_embedding(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        engine.embedding = DummyEmbeddingProvider()
        docs = list(
            DataPipeline.from_jsonl(p, engine=engine)
            .embedding("text")
            .iter_documents()
        )
        for doc in docs:
            assert "vector" in doc


# ===========================================================================
# DataPipeline.save_config() is now a builder (returns self / new pipeline)
# ===========================================================================

class TestSaveConfigAsBuilder:
    def test_save_config_writes_file_immediately(self, tmp_path):
        """save_config() must write the JSON file right away, not at load()."""
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        config_p = tmp_path / "settings.json"
        engine = FakeEngine()
        pipeline = (
            DataPipeline.from_jsonl(p, engine=engine)
            .remove("xxx")
            .save_config(config_p)   # should write NOW, before load/write_jsonl
        )
        assert config_p.exists(), "save_config() must write the file immediately"

    def test_save_config_returns_pipeline(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        engine = FakeEngine()
        pipeline = DataPipeline.from_jsonl(p, engine=engine).remove("xxx")
        result = pipeline.save_config(tmp_path / "cfg.json")
        assert isinstance(result, DataPipeline)

    def test_save_config_chained_with_write_jsonl(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        config_p = tmp_path / "cfg.json"
        out_p = tmp_path / "out.jsonl"
        engine = FakeEngine()
        write_result = (
            DataPipeline.from_jsonl(p, engine=engine)
            .remove("xxx")
            .save_config(config_p)
            .write_jsonl(out_p)
        )
        assert isinstance(write_result, WriteResult)
        assert write_result.count == 3
        assert config_p.exists()

    def test_save_config_chained_with_load(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        config_p = tmp_path / "cfg.json"
        engine = FakeEngine()
        load_result = (
            DataPipeline.from_jsonl(p, engine=engine)
            .remove("xxx")
            .save_config(config_p)
            .load()
        )
        assert isinstance(load_result, LoadResult)
        assert load_result.loaded_count == 3
        assert config_p.exists()

    def test_config_content_correct(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        config_p = tmp_path / "cfg.json"
        engine = FakeEngine()
        DataPipeline.from_jsonl(p, engine=engine) \
            .remove("xxx") \
            .rename("text", "text_en") \
            .save_config(config_p)
        cfg = json.loads(config_p.read_text(encoding="utf-8"))
        assert cfg["version"] == 1
        assert cfg["transforms"][0] == {"type": "remove", "fields": ["xxx"]}
        assert cfg["transforms"][1] == {"type": "rename", "source": "text", "target": "text_en"}


# ===========================================================================
# Pure Python (engine=None) — DataPipeline without SearchEngine / JVM
# ===========================================================================

class TestPurePythonMode:
    """All operations except load() must work with engine=None."""

    def test_from_jsonl_without_engine(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        pipeline = DataPipeline.from_jsonl(p)
        assert pipeline is not None
        assert pipeline.engine is None

    def test_write_jsonl_without_engine(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        out = tmp_path / "out.jsonl"
        result = DataPipeline.from_jsonl(p).remove("xxx").write_jsonl(out)
        assert result.count == 3
        assert out.exists()

    def test_iter_documents_without_engine(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        docs = list(DataPipeline.from_jsonl(p).remove("xxx").iter_documents())
        assert len(docs) == 3
        assert all("xxx" not in d for d in docs)

    def test_attrs_without_engine(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        attrs = DataPipeline.from_jsonl(p).remove("xxx").attrs()
        assert "xxx" not in attrs
        assert "id" in attrs

    def test_head_without_engine(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        docs = DataPipeline.from_jsonl(p).head(2)
        assert len(docs) == 2

    def test_save_config_without_engine(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        cfg = tmp_path / "cfg.json"
        DataPipeline.from_jsonl(p).remove("xxx").save_config(cfg)
        assert cfg.exists()

    def test_load_without_engine_raises(self, tmp_path):
        """load() with engine=None must raise DataPipelineError."""
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        with pytest.raises(DataPipelineError, match="load\\(\\) requires a SearchEngine"):
            DataPipeline.from_jsonl(p).load()

    def test_transforms_applied_without_engine(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        out = tmp_path / "out.jsonl"
        DataPipeline.from_jsonl(p) \
            .remove("xxx") \
            .rename("category", "category_s") \
            .rename("text", "text_en") \
            .write_jsonl(out)
        written = list(JsonlSource(out))
        for doc in written:
            assert "xxx" not in doc
            assert "category_s" in doc
            assert "text_en" in doc


class TestTopLevelDataFunction:
    """Tests for the nlp4j_local_search.data() top-level function."""

    def test_returns_data_pipeline(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        pipeline = data_func(str(p))
        assert isinstance(pipeline, DataPipeline)

    def test_engine_is_none(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        pipeline = data_func(str(p))
        assert pipeline.engine is None

    def test_write_jsonl(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        out = tmp_path / "out.jsonl"
        result = data_func(str(p)).remove("xxx").write_jsonl(out)
        assert result.count == 3

    def test_iter_documents(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        docs = list(data_func(str(p)))
        assert len(docs) == 3

    def test_load_raises_without_engine(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        with pytest.raises(DataPipelineError, match="SearchEngine"):
            data_func(str(p)).load()


class TestEmbeddingProviderArg:
    """Test explicit provider= argument on embedding()."""

    def test_embedding_with_explicit_provider_no_engine(self, tmp_path):
        """embedding(provider=X) must work without a SearchEngine."""
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)

        class LocalProvider:
            @property
            def dimension(self):
                return 2
            def embed_documents(self, texts):
                return [[0.1, 0.2] for _ in texts]

        out = tmp_path / "out.jsonl"
        result = (
            DataPipeline.from_jsonl(p)
            .embedding("text", provider=LocalProvider())
            .write_jsonl(out)
        )
        assert result.count == 3
        written = list(JsonlSource(out))
        for doc in written:
            assert "vector" in doc

    def test_embedding_provider_stored_on_pipeline(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)

        class LocalProvider:
            @property
            def dimension(self):
                return 2
            def embed_documents(self, texts):
                return [[0.0, 1.0] for _ in texts]

        prov = LocalProvider()
        pipeline = DataPipeline.from_jsonl(p).embedding("text", provider=prov)
        assert pipeline.embedding_provider is prov

    def test_embedding_without_provider_and_no_engine_raises(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        with pytest.raises(DataPipelineError, match="Embedding provider is required"):
            DataPipeline.from_jsonl(p).embedding("text").write_jsonl(tmp_path / "out.jsonl")

    def test_embedding_engine_fallback(self, tmp_path):
        """Without explicit provider, engine.embedding is used as fallback."""
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)

        class LocalProvider:
            @property
            def dimension(self):
                return 2
            def embed_documents(self, texts):
                return [[1.0, 0.0] for _ in texts]

        engine = FakeEngine()
        engine.embedding = LocalProvider()
        out = tmp_path / "out.jsonl"
        DataPipeline.from_jsonl(p, engine=engine).embedding("text").write_jsonl(out)
        written = list(JsonlSource(out))
        for doc in written:
            assert "vector" in doc


class TestDataPipelineErrors:
    """Tests for DataPipelineError / DataWriteError raised by the pipeline."""

    def test_load_without_engine_is_data_pipeline_error(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        with pytest.raises(DataPipelineError):
            DataPipeline.from_jsonl(p).load()

    def test_data_pipeline_error_is_exception(self):
        assert issubclass(DataPipelineError, Exception)

    def test_data_write_error_is_data_pipeline_error(self):
        from nlp4j_local_search.data.errors import DataWriteError
        assert issubclass(DataWriteError, DataPipelineError)

    def test_data_load_error_is_data_pipeline_error(self):
        from nlp4j_local_search.data.errors import DataLoadError
        assert issubclass(DataLoadError, DataPipelineError)

    def test_data_source_error_is_data_pipeline_error(self):
        from nlp4j_local_search.data.errors import DataSourceError
        assert issubclass(DataSourceError, DataPipelineError)


# ===========================================================================
# write_jsonl() — same-path guard & atomic write
# ===========================================================================

class TestWriteJsonlSafety:
    def test_same_input_output_raises(self, tmp_path):
        """write_jsonl() must refuse to overwrite the source file."""
        from nlp4j_local_search.data.errors import DataWriteError
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        with pytest.raises(DataWriteError, match="Input and output paths must be different"):
            DataPipeline.from_jsonl(p).write_jsonl(p)

    def test_same_path_via_symlink_raises(self, tmp_path):
        """resolve() must detect same file via different path representations."""
        from nlp4j_local_search.data.errors import DataWriteError
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        # Use str(p) vs Path(p) — both resolve to same file
        with pytest.raises(DataWriteError):
            DataPipeline.from_jsonl(str(p)).write_jsonl(Path(p))

    def test_different_paths_are_fine(self, tmp_path):
        """write_jsonl() to a different path must succeed normally."""
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        out = tmp_path / "out.jsonl"
        result = DataPipeline.from_jsonl(p).write_jsonl(out)
        assert result.count == 3
        assert out.exists()

    def test_atomic_write_produces_correct_output(self, tmp_path):
        """The final file must contain the correct content after atomic replace."""
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        out = tmp_path / "out.jsonl"
        DataPipeline.from_jsonl(p).remove("xxx").write_jsonl(out)
        docs = list(JsonlSource(out))
        assert len(docs) == 3
        assert all("xxx" not in d for d in docs)

    def test_tmp_file_removed_on_success(self, tmp_path):
        """No .tmp file should remain after a successful write."""
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        out = tmp_path / "out.jsonl"
        DataPipeline.from_jsonl(p).write_jsonl(out)
        tmp_file = out.with_suffix(out.suffix + ".tmp")
        assert not tmp_file.exists()

    def test_tmp_file_cleaned_up_on_error(self, tmp_path):
        """On transform failure, the .tmp file must be removed."""
        from nlp4j_local_search.data.transform import RemoveTransform

        class ExplodingTransform:
            """A transform that raises after writing some docs."""
            fields = ("xxx",)
            def apply(self, doc):
                raise RuntimeError("deliberate failure")
            def to_config(self):
                return {"type": "remove", "fields": []}

        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        out = tmp_path / "out.jsonl"
        engine = FakeEngine()
        pipeline = DataPipeline.from_jsonl(p, engine=engine)
        # Inject bad transform manually via replace
        from dataclasses import replace as dc_replace
        bad_pipeline = dc_replace(pipeline, transforms=(ExplodingTransform(),))

        with pytest.raises(RuntimeError, match="deliberate failure"):
            bad_pipeline.write_jsonl(out)

        tmp_file = out.with_suffix(out.suffix + ".tmp")
        assert not tmp_file.exists()


# ===========================================================================
# head() — size validation
# ===========================================================================

class TestHeadValidation:
    def test_negative_size_raises(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        pipeline = DataPipeline.from_jsonl(p)
        with pytest.raises(DataPipelineError, match="size must be >= 0"):
            pipeline.head(-1)

    def test_negative_size_raises_large(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        pipeline = DataPipeline.from_jsonl(p)
        with pytest.raises(DataPipelineError, match="size must be >= 0"):
            pipeline.head(-100)

    def test_zero_size_returns_empty(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        pipeline = DataPipeline.from_jsonl(p)
        assert pipeline.head(0) == []

    def test_positive_size_works(self, tmp_path):
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)
        pipeline = DataPipeline.from_jsonl(p)
        assert len(pipeline.head(2)) == 2


# ===========================================================================
# embedding() — one-provider-per-pipeline constraint documented in tests
# ===========================================================================

class TestEmbeddingOneProviderConstraint:
    """Verify the documented 1 DataPipeline = 1 EmbeddingProvider behaviour."""

    def test_second_provider_overwrites_first(self, tmp_path):
        """The last provider= supplied wins."""
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)

        class ProviderA:
            @property
            def dimension(self): return 2
            def embed_documents(self, texts): return [[1.0, 0.0] for _ in texts]

        class ProviderB:
            @property
            def dimension(self): return 2
            def embed_documents(self, texts): return [[0.0, 1.0] for _ in texts]

        a, b = ProviderA(), ProviderB()
        pipeline = (
            DataPipeline.from_jsonl(p)
            .embedding("text", "vec_a", provider=a)
            .embedding("text", "vec_b", provider=b)
        )
        # pipeline.embedding_provider must be ProviderB (last supplied)
        assert pipeline.embedding_provider is b

    def test_single_provider_applied_to_all_embedding_transforms(self, tmp_path):
        """Both embedding transforms use the same single provider."""
        p = _make_jsonl(tmp_path, SAMPLE_DOCS)

        called_with: list = []

        class TrackingProvider:
            @property
            def dimension(self): return 2
            def embed_documents(self, texts):
                called_with.extend(texts)
                return [[0.5, 0.5] for _ in texts]

        prov = TrackingProvider()
        out = tmp_path / "out.jsonl"
        (
            DataPipeline.from_jsonl(p)
            .embedding("text", "vec1", provider=prov)
            .embedding("text", "vec2", provider=prov)
            .write_jsonl(out)
        )
        # Both transforms should have been executed (2 * 3 = 6 texts called)
        assert len(called_with) == 6
