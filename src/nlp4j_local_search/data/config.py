"""PipelineConfig — serialise/deserialise a DataPipeline as JSON."""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .pipeline import DataPipeline

_VERSION = 1


class PipelineConfig:
    """Converts a :class:`DataPipeline` to/from a JSON config file.

    The generated JSON is human-readable and version-stamped so it can
    serve as a reproducibility record.

    Example config (v1)::

        {
          "version": 1,
          "source": {"type": "jsonl", "path": "test.jsonl"},
          "transforms": [
            {"type": "remove", "fields": ["xxx"]},
            {"type": "rename", "source": "category", "target": "category_s"}
          ],
          "output": {"type": "jsonl", "path": "test2.jsonl"}
        }
    """

    @staticmethod
    def from_pipeline(pipeline: "DataPipeline") -> Dict[str, Any]:
        """Build a config dict from a DataPipeline."""
        config: Dict[str, Any] = {
            "version": _VERSION,
            "source": pipeline.source.to_config(),
            "transforms": [t.to_config() for t in pipeline.transforms],
        }
        if pipeline.output_path is not None:
            config["output"] = {
                "type": "jsonl",
                "path": str(pipeline.output_path),
            }
        return config

    @staticmethod
    def save(pipeline: "DataPipeline", path: str | Path) -> None:
        """Write the pipeline config to *path* as pretty-printed JSON."""
        config = PipelineConfig.from_pipeline(pipeline)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
