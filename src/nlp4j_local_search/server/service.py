import json
import threading
import time

from dataclasses import dataclass
from typing import Any

from nlp4j_local_search import SearchEngine

from .models import SearchRequest
from .plan import (
    LexicalSearchPlan,
    VectorSearchPlan,
)
from .query import QueryPlanner


@dataclass
class ServerConfig:

    lang: str = "en"

    index_name: str = "default"

    auto_analyze: bool = False

    data_path: str | None = None


class SearchService:

    def __init__(
        self,
        engine: SearchEngine,
        index_name: str,
    ):

        self.engine = engine

        self.index_name = index_name

        self.lock = threading.RLock()

        self.planner = QueryPlanner(
            self.field_type
        )

    # --------------------------------------------------
    # index
    # --------------------------------------------------

    def check_index(
        self,
        index: str | None,
    ) -> None:

        if index is None:
            return

        if index != self.index_name:
            raise KeyError(index)

    # --------------------------------------------------
    # search
    # --------------------------------------------------

    def search(
        self,
        request: SearchRequest,
    ) -> dict[str, Any]:

        started = time.perf_counter()

        plan = self.planner.build(
            request.query,
            size=request.size,
            offset=request.from_,
        )

        if isinstance(
            plan,
            LexicalSearchPlan,
        ):

            response = (
                self._search_lexical(
                    plan,
                    request,
                )
            )

        elif isinstance(
            plan,
            VectorSearchPlan,
        ):

            response = (
                self._search_vector(
                    plan,
                    request,
                )
            )

        else:

            raise RuntimeError(
                "Unknown SearchPlan"
            )

        response["took"] = int(
            (
                time.perf_counter()
                - started
            )
            * 1000
        )

        response["timed_out"] = False

        response["_shards"] = {
            "total": 1,
            "successful": 1,
            "skipped": 0,
            "failed": 0,
        }

        return response

    # --------------------------------------------------
    # lexical
    # --------------------------------------------------

    def _search_lexical(
        self,
        plan: LexicalSearchPlan,
        request: SearchRequest,
    ) -> dict[str, Any]:

        limit = (
            request.from_
            + request.size
        )

        # size=0 の場合は count のみ
        if limit == 0:
            total = self._count(plan.lucene_query)
            return self._hits_response(hits=[], total=total)

        with self.lock:

            results = list(
                self.engine.search(
                    plan.lucene_query,
                    limit=limit,
                )
            )

        selected = results[
            request.from_:
            request.from_
            + request.size
        ]

        hits = [
            self._convert_hit(
                result,
                request.source,
            )
            for result in selected
        ]

        total = self._count(
            plan.lucene_query
        )

        return self._hits_response(
            hits=hits,
            total=total,
        )

    # --------------------------------------------------
    # vector
    # --------------------------------------------------

    def _search_vector(
        self,
        plan: VectorSearchPlan,
        request: SearchRequest,
    ) -> dict[str, Any]:

        if plan.query_text is not None:
            # テキストクエリ → search_vector_by_text() に委譲
            with self.lock:
                results = list(
                    self.engine.search_vector_by_text(
                        plan.query_text,
                        limit=plan.k,
                        field=plan.field,
                        filter_query=plan.filter_query,
                    )
                )
        else:
            # ベクトルクエリ → search_vector() に委譲
            with self.lock:
                results = list(
                    self.engine.search_vector(
                        plan.query_vector,
                        limit=plan.k,
                        field=plan.field,
                        filter_query=plan.filter_query,
                    )
                )

        selected = results[
            request.from_:
            request.from_
            + request.size
        ]

        hits = [
            self._convert_hit(
                result,
                request.source,
            )
            for result in selected
        ]

        return self._hits_response(
            hits=hits,
            total=len(results),
        )

    # --------------------------------------------------
    # count
    # --------------------------------------------------

    def count(
        self,
        query: dict | None,
    ) -> dict[str, Any]:

        plan = self.planner.build(
            query,
            size=0,
        )

        if not isinstance(
            plan,
            LexicalSearchPlan,
        ):

            raise ValueError(
                "_count does not support "
                "VECTOR queries"
            )

        return {
            "count": self._count(
                plan.lucene_query
            ),
            "_shards": {
                "total": 1,
                "successful": 1,
                "skipped": 0,
                "failed": 0,
            },
        }

    def _count(
        self,
        lucene_query: str,
    ) -> int:

        with self.lock:

            if lucene_query == "*:*":
                return int(
                    self.engine.count()
                )

            return int(
                self.engine.count(
                    lucene_query
                )
            )

    # --------------------------------------------------
    # field information
    # --------------------------------------------------

    def field_type(
        self,
        field: str,
    ) -> str:

        info = self.field_info(
            field
        )

        field_type = info.get(
            "type"
        )

        if not field_type:

            raise ValueError(
                f"Unknown field: {field}"
            )

        return str(field_type)

    def field_info(
        self,
        field: str,
    ) -> dict[str, Any]:

        value = self.engine.field_info(field)

        if value is None:
            raise ValueError(f"Unknown field: {field}")

        return {
            "name": value.name,
            "type": value.type,
            "dimension": value.dimension,
            "similarity": value.similarity,
            "model": value.model,
        }

    # --------------------------------------------------
    # mapping
    # --------------------------------------------------

    def mapping(
        self,
    ) -> dict[str, Any]:

        properties = {}

        for name in self.engine.fields():
            info_obj = self.engine.field_info(name)
            if info_obj is None:
                field_info_dict: dict[str, Any] = {"name": name, "type": "TEXT"}
            else:
                field_info_dict = {
                    "name": info_obj.name,
                    "type": info_obj.type,
                    "dimension": info_obj.dimension,
                    "similarity": info_obj.similarity,
                    "model": info_obj.model,
                }
            properties[name] = self._mapping_field(field_info_dict)

        return {
            self.index_name: {
                "mappings": {
                    "properties": properties,
                }
            }
        }

    @staticmethod
    def _mapping_field(
        info: dict[str, Any],
    ) -> dict[str, Any]:

        field_type = str(
            info.get(
                "type",
                "TEXT",
            )
        ).upper()

        mapping = {
            "TEXT": "text",
            "KEYWORD": "keyword",
            "INTEGER": "integer",
            "LONG": "long",
            "DOUBLE": "double",
            "DATE": "date",
        }

        if field_type == "VECTOR":

            result: dict[str, Any] = {
                "type": "dense_vector",
            }

            dimension = info.get(
                "dimension"
            )

            if dimension is not None:
                result["dims"] = dimension

            similarity = info.get(
                "similarity"
            )

            if similarity:
                result[
                    "similarity"
                ] = similarity

            model = info.get(
                "model"
            )

            if model:
                result[
                    "nlp4j_model"
                ] = model

            return result

        return {
            "type": mapping.get(
                field_type,
                "text",
            )
        }

    # --------------------------------------------------
    # result
    # --------------------------------------------------

    def _hits_response(
        self,
        hits: list[dict],
        total: int,
    ) -> dict[str, Any]:

        scores = [
            hit["_score"]
            for hit in hits
            if hit["_score"] is not None
        ]

        return {
            "hits": {
                "total": {
                    "value": total,
                    "relation": "eq",
                },
                "max_score": (
                    max(scores)
                    if scores
                    else None
                ),
                "hits": hits,
            }
        }

    def _convert_hit(
        self,
        result: Any,
        source_filter,
    ) -> dict[str, Any]:

        if isinstance(result, dict):

            source = dict(
                result.get(
                    "_source",
                    result,
                )
            )

            result_id = (
                result.get("_id")
                or result.get("id")
            )

            score = (
                result.get("_score")
                or result.get("score")
            )

        else:

            result_id = getattr(
                result,
                "id",
                None,
            )

            score = getattr(
                result,
                "score",
                None,
            )

            body = getattr(
                result,
                "body",
                None,
            )

            source = (
                self._body_to_dict(
                    body
                )
            )

        source = self._apply_source_filter(
            source,
            source_filter,
        )

        return {
            "_index": self.index_name,
            "_id": (
                str(result_id)
                if result_id is not None
                else None
            ),
            "_score": (
                float(score)
                if score is not None
                else None
            ),
            "_source": source,
        }

    @staticmethod
    def _body_to_dict(
        body: Any,
    ) -> dict[str, Any]:

        if body is None:
            return {}

        if isinstance(body, dict):
            return dict(body)

        if isinstance(body, str):

            try:

                value = json.loads(
                    body
                )

                if isinstance(
                    value,
                    dict,
                ):
                    return value

            except json.JSONDecodeError:
                pass

        return {
            "body": body
        }

    @staticmethod
    def _apply_source_filter(
        source: dict,
        source_filter,
    ) -> dict:

        if source_filter is None:
            return source

        if source_filter is False:
            return {}

        if isinstance(
            source_filter,
            list,
        ):

            return {
                key: value
                for key, value
                in source.items()
                if key in source_filter
            }

        excludes = (
            source_filter.excludes
            or []
        )

        includes = (
            source_filter.includes
            or []
        )

        result = dict(source)

        if includes:

            result = {
                key: value
                for key, value
                in result.items()
                if key in includes
            }

        for field in excludes:
            result.pop(
                field,
                None,
            )

        return result
