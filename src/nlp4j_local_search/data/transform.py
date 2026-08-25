"""Transform classes — pure document transformations (no I/O, no JVM)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator, List, Protocol, Sequence, runtime_checkable

if TYPE_CHECKING:
    from ..embedding import EmbeddingProvider


@runtime_checkable
class Transform(Protocol):
    """Protocol for single-document transformations."""

    def apply(self, doc: dict) -> dict:
        ...

    def to_config(self) -> dict:
        ...


# ---------------------------------------------------------------------------
# RemoveTransform
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RemoveTransform:
    """Remove one or more fields from a document.

    Example::

        t = RemoveTransform(("xxx",))
        result = t.apply({"id": 1, "xxx": "aaa", "text": "hello"})
        # {"id": 1, "text": "hello"}
    """

    fields: tuple

    def apply(self, doc: dict) -> dict:
        result = dict(doc)
        for f in self.fields:
            result.pop(f, None)
        return result

    def to_config(self) -> dict:
        return {
            "type": "remove",
            "fields": list(self.fields),
        }


# ---------------------------------------------------------------------------
# RenameTransform
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RenameTransform:
    """Rename a single field.

    If *source* is absent in the document the document is returned unchanged.

    Example::

        t = RenameTransform("category", "category_s")
        result = t.apply({"id": 1, "category": "city"})
        # {"id": 1, "category_s": "city"}
    """

    source: str
    target: str

    def apply(self, doc: dict) -> dict:
        result = dict(doc)
        if self.source in result:
            result[self.target] = result.pop(self.source)
        return result

    def to_config(self) -> dict:
        return {
            "type": "rename",
            "source": self.source,
            "target": self.target,
        }


# ---------------------------------------------------------------------------
# EmbeddingTransform
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EmbeddingTransform:
    """Add an embedding vector field to documents.

    Unlike the simple transforms, this operates in *batches* for efficiency.
    Call :meth:`apply_batch` instead of ``apply``.

    Example::

        t = EmbeddingTransform(source="text_en", target="vector")
        docs = t.apply_batch([{"id": 1, "text_en": "hello"}], provider)
        # [{"id": 1, "text_en": "hello", "vector": [...]}]
    """

    source: str
    target: str = "vector"
    batch_size: int = 32

    def apply(self, doc: dict) -> dict:
        raise NotImplementedError(
            "EmbeddingTransform must be applied via apply_batch()."
        )

    def apply_batch(
        self,
        docs: List[dict],
        provider: "EmbeddingProvider",
    ) -> List[dict]:
        """Embed a batch of documents and return copies with the vector field added."""
        texts = [str(doc.get(self.source, "")) for doc in docs]
        vectors = provider.embed_documents(texts)
        result = []
        for doc, vector in zip(docs, vectors):
            d = dict(doc)
            d[self.target] = list(vector)
            result.append(d)
        return result

    def to_config(self) -> dict:
        return {
            "type": "embedding",
            "source": self.source,
            "target": self.target,
            "batch_size": self.batch_size,
        }
