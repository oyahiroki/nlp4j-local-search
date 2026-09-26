from typing import List, Protocol, Sequence, runtime_checkable


Vector = List[float]


@runtime_checkable
class EmbeddingProvider(Protocol):
    """
    Interface for converting text into embedding vectors.

    Concrete implementations may use local models,
    remote services, APIs, ONNX models, etc.
    """

    @property
    def dimension(self) -> int:
        """
        Return the dimension of embedding vectors.
        """
        ...

    def embed_query(self, text: str) -> Vector:
        """
        Convert a search query into an embedding vector.
        """
        ...

    def embed_documents(
        self,
        texts: Sequence[str],
    ) -> List[Vector]:
        """
        Convert document texts into embedding vectors.
        """
        ...


class MultilingualE5LargeEmbedding:
    """Default embedding provider backed by nlp4j-local-search-embedding.

    Model:
        intfloat/multilingual-e5-large

    Dimension:
        1024

    Used automatically when ``SearchEngine(embedding=True)`` is specified.
    Requires the ``nlp4j-local-search-embedding`` package::

        pip install nlp4j-local-search-embedding
    """

    MODEL_NAME = "intfloat/multilingual-e5-large"
    DIMENSION = 1024

    def __init__(self) -> None:
        try:
            from nlp4j_local_search_embedding import E5Embedder  # noqa: PLC0415
        except ImportError as e:
            raise ImportError(
                "embedding=True requires the 'nlp4j-local-search-embedding' package.\n"
                "Install it with:\n\n"
                "    pip install nlp4j-local-search-embedding\n"
            ) from e

        self._embedder = E5Embedder(
            model_name=self.MODEL_NAME,
            show_progress_bar=False,
        )

    @property
    def dimension(self) -> int:
        return self.DIMENSION

    def embed_query(self, text: str) -> Vector:
        return list(self._embedder.embed_query(text))

    def embed_documents(self, texts: Sequence[str]) -> List[Vector]:
        return [list(v) for v in self._embedder.embed_documents(texts)]


def create_default_embedding() -> "MultilingualE5LargeEmbedding":
    """Instantiate the default embedding provider (Multilingual-E5-large)."""
    return MultilingualE5LargeEmbedding()
