from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


def _normalize_field_type(kind: str) -> str:
    """Java の KNN_VECTOR を Python API では VECTOR に正規化する。"""
    if kind == "KNN_VECTOR":
        return "VECTOR"
    return kind


@dataclass(frozen=True)
class FieldInfo:
    """フィールドのスキーマ情報を保持するデータクラス。

    :meth:`~nlp4j_local_search.engine.SearchEngine.field_info` の戻り値。
    """

    name: str
    type: str

    stored: bool
    aggregatable: bool
    sortable: bool
    range: bool
    multi_valued: bool

    # VECTOR フィールドのみ
    dimension: Optional[int] = None
    similarity: Optional[str] = None
    model: Optional[str] = None


_VALID_SIMILARITIES = frozenset({
    "cosine",
    "dot_product",
    "euclidean",
    "maximum_inner_product",
})


@dataclass(frozen=True)
class VectorFieldConfig:
    """ベクトルフィールドの定義。

    :class:`~nlp4j_local_search.engine.SearchEngine` コンストラクタの
    ``vector_fields`` に渡す。

    例::

        SearchEngine(
            lang="en",
            vector_fields={
                "vector3": VectorFieldConfig(dimension=3, similarity="cosine", model="demo-3d"),
            },
        )
    """

    dimension: int
    similarity: str = "cosine"
    model: Optional[str] = None

    def __post_init__(self) -> None:
        if self.dimension <= 0:
            raise ValueError(
                f"VectorFieldConfig.dimension must be greater than 0, got {self.dimension}"
            )
        if self.similarity.lower() not in _VALID_SIMILARITIES:
            raise ValueError(
                f"VectorFieldConfig.similarity must be one of "
                f"{sorted(_VALID_SIMILARITIES)}, got {self.similarity!r}"
            )
