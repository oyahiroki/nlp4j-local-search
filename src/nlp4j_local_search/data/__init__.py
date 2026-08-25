"""nlp4j_local_search.data — data import and transformation subpackage."""
from .pipeline import DataPipeline
from .result import LoadResult, WriteResult
from .source import DataSource, JsonlSource
from .transform import EmbeddingTransform, RemoveTransform, RenameTransform
from .sink import JsonlSink
from .config import PipelineConfig
from .errors import DataPipelineError, DataSourceError, DataWriteError, DataLoadError


def data(path: str) -> DataPipeline:
    """Open a JSONL file and return a :class:`DataPipeline` — no JVM required.

    Convenience shortcut for :meth:`DataPipeline.from_jsonl` without an engine.
    Use this for pure data-prep workflows that do not need LocalSearch::

        from nlp4j_local_search import data

        result = (
            data("input.jsonl")
                .remove("xxx")
                .rename("category", "category_s")
                .write_jsonl("output.jsonl")
        )
    """
    return DataPipeline.from_jsonl(path)


__all__ = [
    "data",
    "DataPipeline",
    "LoadResult",
    "WriteResult",
    "DataSource",
    "JsonlSource",
    "RemoveTransform",
    "RenameTransform",
    "EmbeddingTransform",
    "JsonlSink",
    "PipelineConfig",
    "DataPipelineError",
    "DataSourceError",
    "DataWriteError",
    "DataLoadError",
]
