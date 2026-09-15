"""DataPipeline — immutable fluent pipeline for data import and transformation.

DataPipeline works in two modes:

Pure Python (no JVM required)::

    from nlp4j_local_search import data

    result = (
        data("input.jsonl")
            .remove("xxx")
            .rename("category", "category_s")
            .write_jsonl("output.jsonl")
    )

LocalSearch integration (JVM required, engine must be supplied)::

    with SearchEngine("en") as engine:
        result = (
            engine.data("input.jsonl")
                  .remove("xxx")
                  .rename("category", "category_s")
                  .load()
        )
"""
from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterator, Optional, Tuple

from .config import PipelineConfig
from .errors import DataLoadError, DataPipelineError, DataWriteError
from .result import LoadResult, WriteResult
from .sink import JsonlSink
from .source import JsonlSource
from .transform import EmbeddingTransform

if TYPE_CHECKING:
    from ..embedding import EmbeddingProvider
    from ..engine import SearchEngine


@dataclass(frozen=True)
class DataPipeline:
    """Immutable, chainable pipeline for JSONL data transformation.

    Every builder method returns a *new* DataPipeline instance so the original
    is never modified — the same pattern as :class:`ViewResult`.

    **engine is optional.**  Only :meth:`load` requires a SearchEngine.
    All other operations (:meth:`write_jsonl`, :meth:`iter_documents`,
    :meth:`attrs`, :meth:`head`) work without one.

    Terminal operations:

    * :meth:`write_jsonl` — process and save to a JSONL file (no JVM needed)
    * :meth:`load`        — process and load into the SearchEngine (JVM required)

    Metadata operation:

    * :meth:`save_config` — save the pipeline definition as JSON (returns self)

    Iteration:

    * :meth:`iter_documents` / ``__iter__`` — iterate processed dicts directly

    Typical usage::

        # Pure Python — no SearchEngine, no JVM
        from nlp4j_local_search import data

        result = (
            data("test.jsonl")
                .remove("xxx")
                .rename("category", "category_s")
                .write_jsonl("test2.jsonl")
        )
        print(result)
        # Wrote 3 documents to test2.jsonl in 0.01 seconds.

        # LocalSearch integration
        with SearchEngine("en") as engine:
            result = (
                engine.data("test.jsonl")
                      .remove("xxx")
                      .load()
            )
    """

    source: object
    transforms: Tuple = ()
    engine: Optional[object] = None          # None → pure-Python mode
    embedding_provider: Optional[object] = None  # explicit provider; falls back to engine.embedding
    output_path: Optional[Path] = None       # used only by load() for simultaneous save
    config_path: Optional[Path] = None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_jsonl(
        cls,
        path: "str | Path",
        *,
        engine: "Optional[SearchEngine]" = None,
    ) -> "DataPipeline":
        """Create a pipeline backed by a JSONL file.

        *engine* is optional.  Omit it for pure-Python data preparation::

            DataPipeline.from_jsonl("input.jsonl")

        Supply *engine* when you intend to call :meth:`load`::

            DataPipeline.from_jsonl("input.jsonl", engine=search_engine)
        """
        return cls(source=JsonlSource(path), engine=engine)

    # ------------------------------------------------------------------
    # Builder methods (each returns a new immutable DataPipeline)
    # ------------------------------------------------------------------

    def remove(self, *fields: str) -> "DataPipeline":
        """Add a :class:`RemoveTransform` that drops the given field names."""
        from .transform import RemoveTransform
        return replace(
            self,
            transforms=self.transforms + (RemoveTransform(fields),),
        )

    def rename(self, source: str, target: str) -> "DataPipeline":
        """Add a :class:`RenameTransform` that renames *source* → *target*."""
        from .transform import RenameTransform
        return replace(
            self,
            transforms=self.transforms + (RenameTransform(source, target),),
        )

    def embedding(
        self,
        source: str,
        target: str = "vector",
        *,
        provider: "Optional[EmbeddingProvider]" = None,
        batch_size: int = 32,
    ) -> "DataPipeline":
        """Add an :class:`EmbeddingTransform` that writes vectors to *target*.

        **One provider per pipeline.**  A ``DataPipeline`` holds a single
        ``embedding_provider``.  If you call ``.embedding()`` multiple times
        with different ``provider=`` values, the *last* supplied provider wins
        for the whole pipeline.  To use different providers per field, create
        separate pipelines.

        Provider resolution order at execution time:

        1. ``provider`` argument passed here (highest priority)
        2. ``pipeline.embedding_provider`` set on this instance
        3. ``engine.embedding`` (only when an engine is attached)

        Example — pure Python, no SearchEngine::

            from nlp4j_local_search import data

            result = (
                data("input.jsonl")
                    .embedding("text_en", provider=my_embedding)
                    .write_jsonl("output.jsonl")
            )
        """
        new_provider = provider  # store explicit provider on the pipeline
        return replace(
            self,
            transforms=self.transforms + (
                EmbeddingTransform(source=source, target=target, batch_size=batch_size),
            ),
            # Override embedding_provider only if explicitly given here
            embedding_provider=(
                new_provider if new_provider is not None else self.embedding_provider
            ),
        )

    def save_as(self, path: "str | Path") -> "DataPipeline":
        """Record *path* so that :meth:`load` also saves a JSONL copy.

        .. note::
            To save JSONL *without* loading into the index, use
            :meth:`write_jsonl` — it is a cleaner terminal operation.
        """
        return replace(self, output_path=Path(path))

    def save_config(self, path: "str | Path") -> "DataPipeline":
        """Save the pipeline definition to *path* (JSON) immediately and return self.

        This is a **metadata operation** — it writes the config now and returns
        the same pipeline so chaining continues::

            pipeline.save_config("settings.json").write_jsonl("out.jsonl")
            pipeline.save_config("settings.json").load()
        """
        PipelineConfig.save(self, path)
        return replace(self, config_path=Path(path))

    # ------------------------------------------------------------------
    # Terminal operations
    # ------------------------------------------------------------------

    def write_jsonl(self, path: "str | Path") -> WriteResult:
        """Process the pipeline and write all documents to *path* as JSONL.

        **No SearchEngine or JVM required.**

        Uses an atomic write strategy: documents are first written to a
        temporary file next to *path*, then renamed into place with
        :func:`os.replace`.  This ensures that a partial failure (e.g. a
        transform error mid-stream) never produces a truncated output file.

        Raises :class:`DataWriteError` if *path* resolves to the same file as
        the pipeline's source (overwriting the input is not allowed).

        Example::

            from nlp4j_local_search import data

            result = (
                data("input.jsonl")
                    .remove("xxx")
                    .rename("category", "category_s")
                    .write_jsonl("output.jsonl")
            )
            print(result)
            # Wrote 3 documents to output.jsonl in 0.01 seconds.
        """
        provider = self._resolve_provider()
        output_path = Path(path)

        # Guard: refuse to overwrite the source file
        source_path = getattr(self.source, "path", None)
        if source_path is not None:
            try:
                if output_path.resolve() == Path(source_path).resolve():
                    raise DataWriteError(
                        f"Input and output paths must be different: {output_path}"
                    )
            except OSError:
                pass  # resolve() can fail on non-existent paths — skip the check

        start = time.perf_counter()
        count = 0
        tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")

        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                for doc in self._iter_transformed(provider):
                    f.write(json.dumps(doc, ensure_ascii=False) + "\n")
                    count += 1
            os.replace(tmp_path, output_path)
        except DataWriteError:
            raise
        except OSError as e:
            raise DataWriteError(f"Failed to write {output_path}: {e}") from e
        except Exception:
            # Clean up the temp file on any other error
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise

        elapsed = time.perf_counter() - start
        return WriteResult(
            path=str(output_path),
            count=count,
            elapsed_seconds=elapsed,
        )

    def load(
        self,
        *,
        progress_callback: Callable[[int, float], None] | None = None,
        progress_interval_seconds: float = 1.0,
    ) -> LoadResult:
        """Process the pipeline and load all documents into the SearchEngine.

        **Requires a SearchEngine** — raises :class:`DataPipelineError` when
        called on a pipeline created without one (i.e. via ``data(path)``).
        Use ``engine.data(path).load()`` instead.

        Optionally saves a JSONL copy when :meth:`save_as` was called.

        Args:
            progress_callback:
                Optional callback called periodically while documents are loaded.
                The callback receives ``(loaded_count, elapsed_seconds)``.
            progress_interval_seconds:
                Minimum interval between progress callback invocations.
        """
        if self.engine is None:
            raise DataPipelineError(
                "load() requires a SearchEngine. "
                "Use engine.data(...) to load documents into LocalSearch."
            )

        provider = self._resolve_provider()

        start = time.perf_counter()
        last_progress_at = start

        read_count = 0
        loaded_count = 0
        written_count = 0

        sink_ctx = (
            JsonlSink(self.output_path)
            if self.output_path is not None
            else _null_context()
        )

        try:
            with sink_ctx as sink:
                for doc in self._iter_transformed(provider):
                    read_count += 1

                    if sink is not None:
                        sink.write(doc)
                        written_count += 1

                    self.engine.add_json(doc)
                    loaded_count += 1

                    if progress_callback is not None:
                        now = time.perf_counter()
                        if now - last_progress_at >= progress_interval_seconds:
                            progress_callback(loaded_count, now - start)
                            last_progress_at = now

            self.engine.commit()

        except DataPipelineError:
            raise
        except Exception as e:
            raise DataLoadError(
                f"Failed to load documents into SearchEngine: {e}"
            ) from e

        elapsed = time.perf_counter() - start

        if progress_callback is not None:
            progress_callback(loaded_count, elapsed)

        return LoadResult(
            read_count=read_count,
            loaded_count=loaded_count,
            written_count=written_count,
            elapsed_seconds=elapsed,
            output_path=self.output_path,
        )

    # ------------------------------------------------------------------
    # Iteration API
    # ------------------------------------------------------------------

    def iter_documents(self) -> Iterator[dict]:
        """Iterate over fully-transformed documents without indexing or saving.

        No SearchEngine or JVM required::

            for doc in data("input.jsonl").remove("xxx").iter_documents():
                print(doc)
        """
        provider = self._resolve_provider()
        return self._iter_transformed(provider)

    def __iter__(self) -> Iterator[dict]:
        """Iterate over fully-transformed documents (same as :meth:`iter_documents`).

        Enables Pythonic usage::

            docs = list(data("input.jsonl").remove("xxx").rename("a", "b"))
        """
        return self.iter_documents()

    def attrs(self) -> "list[str]":
        """Return the field names of the **first** transformed document.

        Only the first document is read — this is fast and constant-memory,
        but the returned field list reflects only that document's keys.
        If documents have inconsistent schemas (e.g. some rows have extra
        fields), later rows may have additional fields not shown here.

        Returns an empty list if the source is empty.
        No SearchEngine or JVM required::

            data("input.jsonl").remove("xxx").attrs()
            # ['id', 'category', 'text']
        """
        for doc in self.iter_documents():
            return list(doc.keys())
        return []

    def head(self, size: int = 1) -> "list[dict]":
        """Return the first *size* transformed documents without indexing.

        Defaults to 1 so that ``pipeline.head()`` shows one representative
        document.  No SearchEngine or JVM required::

            data("input.jsonl").head(3)

        Raises :class:`DataPipelineError` if *size* is negative.
        """
        if size < 0:
            raise DataPipelineError(
                f"head() size must be >= 0, got {size}"
            )
        from itertools import islice
        return list(islice(self.iter_documents(), size))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_provider(self):
        """Return the embedding provider to use, or None if not needed.

        Resolution order:
        1. ``self.embedding_provider`` (set via ``embedding(..., provider=X)``)
        2. ``engine.embedding`` (fallback when engine is attached)

        Raises :class:`DataPipelineError` if an EmbeddingTransform is present
        but no provider can be found.
        """
        has_embedding = any(isinstance(t, EmbeddingTransform) for t in self.transforms)
        if not has_embedding:
            return None

        # 1. Explicit provider stored on this pipeline instance
        provider = self.embedding_provider

        # 2. Fallback to engine.embedding
        if provider is None and self.engine is not None:
            provider = getattr(self.engine, "embedding", None)

        if provider is None:
            raise DataPipelineError(
                "Embedding provider is required for embedding(). "
                "Pass provider=<provider> to embedding(), or attach a SearchEngine "
                "that has embedding= set."
            )
        return provider

    def _iter_transformed(self, provider) -> Iterator[dict]:
        """Yield fully-transformed documents one at a time.

        Transforms are applied in order.  EmbeddingTransforms are batched
        for efficiency; all other transforms run per-document.
        """
        # Build phases: list of (tuple_of_doc_transforms, embedding_or_None)
        phases = []
        pending = []
        for t in self.transforms:
            if isinstance(t, EmbeddingTransform):
                phases.append((tuple(pending), t))
                pending = []
            else:
                pending.append(t)
        phases.append((tuple(pending), None))

        def apply_doc_tforms(doc, tforms):
            for t in tforms:
                doc = t.apply(doc)
            return doc

        has_embedding = any(emb is not None for _, emb in phases)

        if not has_embedding:
            doc_tforms = phases[0][0]
            for raw_doc in self.source:
                yield apply_doc_tforms(raw_doc, doc_tforms)
            return

        batch_size = min(
            t.batch_size
            for t in self.transforms
            if isinstance(t, EmbeddingTransform)
        )

        buffer: list = []
        for raw_doc in self.source:
            buffer.append(raw_doc)
            if len(buffer) >= batch_size:
                yield from self._flush(buffer, phases, provider, apply_doc_tforms)
                buffer = []
        if buffer:
            yield from self._flush(buffer, phases, provider, apply_doc_tforms)

    def _flush(self, buffer, phases, provider, apply_doc_tforms) -> Iterator[dict]:
        """Apply all phases to a buffer of raw docs and yield individual dicts."""
        docs = list(buffer)
        for doc_tforms, emb_transform in phases:
            docs = [apply_doc_tforms(d, doc_tforms) for d in docs]
            if emb_transform is not None:
                docs = emb_transform.apply_batch(docs, provider)
        yield from docs


# ------------------------------------------------------------------
# Null context manager helper
# ------------------------------------------------------------------

@contextmanager
def _null_context():
    yield None
