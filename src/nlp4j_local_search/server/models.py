from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SourceFilter(BaseModel):

    includes: list[str] | None = None
    excludes: list[str] | None = None


class SearchRequest(BaseModel):

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )

    query: dict[str, Any] | None = None

    size: int = Field(
        default=10,
        ge=0,
    )

    from_: int = Field(
        default=0,
        alias="from",
        ge=0,
    )

    source: (
        bool
        | list[str]
        | SourceFilter
        | None
    ) = Field(
        default=None,
        alias="_source",
    )

    aggs: dict[str, Any] | None = None

    aggregations: dict[str, Any] | None = None


class CountRequest(BaseModel):

    query: dict[str, Any] | None = None
