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
