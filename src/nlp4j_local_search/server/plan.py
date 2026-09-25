from dataclasses import dataclass
from typing import Optional


@dataclass
class SearchPlan:
    pass


@dataclass
class LexicalSearchPlan(SearchPlan):

    lucene_query: str


@dataclass
class VectorSearchPlan(SearchPlan):

    field: str

    query_text: Optional[str] = None

    query_vector: Optional[list[float]] = None

    model_id: Optional[str] = None

    k: int = 10

    num_candidates: Optional[int] = None

    filter_query: Optional[str] = None
