"""DataShellContext — mutable state held across commands in the REPL."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ...data.pipeline import DataPipeline


@dataclass
class DataShellContext:
    """Holds the current pipeline and undo history for the interactive shell.

    Every pipeline-mutating command must:
    1. Push the old pipeline onto ``history`` before updating.
    2. Set ``pipeline`` to the new DataPipeline instance.

    This allows :class:`~nlp4j_local_search.cli.data.commands.UndoCommand` to pop
    the last state off ``history``.
    """

    pipeline: Optional[DataPipeline] = None
    """Current pipeline, or None if no data source has been opened yet."""

    history: list = field(default_factory=list)
    """Undo stack — list of DataPipeline snapshots (oldest first)."""

    def push_history(self) -> None:
        """Snapshot the current pipeline onto the undo stack."""
        if self.pipeline is not None:
            self.history.append(self.pipeline)

    def require_pipeline(self) -> DataPipeline:
        """Return the current pipeline or raise CommandError if not set."""
        if self.pipeline is None:
            raise CommandError("No data source loaded. Use: data <path>")
        return self.pipeline


class CommandError(Exception):
    """Raised when a command receives wrong arguments or encounters a usage error."""
