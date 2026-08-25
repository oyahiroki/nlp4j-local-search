"""Errors for the nlp4j_local_search.data subpackage.

These are raised by pure-Python DataPipeline operations and are intentionally
separate from the JVM-related errors in nlp4j_local_search.errors so that
data-prep code never imports from the engine layer.
"""
from __future__ import annotations


class DataPipelineError(Exception):
    """Base class for all data pipeline errors."""


class DataSourceError(DataPipelineError):
    """Raised when a data source cannot be read (file not found, invalid JSON, etc.)."""


class DataWriteError(DataPipelineError):
    """Raised when writing output fails (permissions, disk full, etc.)."""


class DataLoadError(DataPipelineError):
    """Raised when loading documents into a SearchEngine fails.

    This is the only error in this module that originates from JVM/Lucene code.
    The original Java exception is available as ``__cause__``.
    """
