import re
from typing import Any, Callable

from .plan import (
    LexicalSearchPlan,
    SearchPlan,
    VectorSearchPlan,
)


class QueryError(ValueError):
    pass


class UnsupportedQueryError(QueryError):
    pass


_FIELD_PATTERN = re.compile(
    r"^[A-Za-z0-9_.-]+$"
)


def _validate_field(
    field: str,
) -> str:

    if not _FIELD_PATTERN.match(field):

        raise QueryError(
            f"Invalid field name: {field}"
        )

    return field


def _quote(
    value: Any,
) -> str:

    text = str(value)

    text = text.replace(
        "\\",
        "\\\\",
    )

    text = text.replace(
        '"',
        '\\"',
    )

    return f'"{text}"'


def _match_value(
    value: Any,
) -> str:

    text = str(value)

    if re.match(
        r'^[^\s():+\-!{}\[\]^"~*?\\/]+$',
        text,
    ):
        return text

    return _quote(text)


class QueryPlanner:

    def __init__(
        self,
        field_type_resolver: Callable[[str], str],
    ):

        self.field_type_resolver = (
            field_type_resolver
        )

    # --------------------------------------------------
    # public
    # --------------------------------------------------

    def build(
        self,
        query: dict[str, Any] | None,
        size: int,
        offset: int = 0,
    ) -> SearchPlan:

        if query is None:

            return LexicalSearchPlan(
                "*:*"
            )

        return self._build(
            query,
            size=size,
            offset=offset,
        )

    # --------------------------------------------------
    # internal
    # --------------------------------------------------

    def _build(
        self,
        query: dict[str, Any],
        size: int,
        offset: int,
    ) -> SearchPlan:

        if not isinstance(query, dict):

            raise QueryError(
                "query must be an object"
            )

        if len(query) != 1:

            raise QueryError(
                "query must contain exactly "
                "one query type"
            )

        query_type, body = next(
            iter(query.items())
        )

        if query_type == "match_all":

            return LexicalSearchPlan(
                "*:*"
            )

        if query_type == "query_string":

            return LexicalSearchPlan(
                self._query_string(body)
            )

        if query_type == "term":

            return LexicalSearchPlan(
                self._term(body)
            )

        if query_type == "range":

            return LexicalSearchPlan(
                self._range(body)
            )

        if query_type == "match":

            return self._match(
                body,
                size=size,
                offset=offset,
            )

        if query_type == "knn":

            return self._knn(
                body,
                size=size,
                offset=offset,
            )

        if query_type == "bool":

            return self._bool(
                body,
                size=size,
                offset=offset,
            )

        raise UnsupportedQueryError(
            f"Unsupported query type: "
            f"{query_type}"
        )

    # --------------------------------------------------
    # query_string
    # --------------------------------------------------

    def _query_string(
        self,
        body: Any,
    ) -> str:

        if isinstance(body, str):
            return body

        if not isinstance(body, dict):

            raise QueryError(
                "query_string must be an object"
            )

        value = body.get("query")

        if not value:

            raise QueryError(
                "query_string.query is required"
            )

        return str(value)

    # --------------------------------------------------
    # term
    # --------------------------------------------------

    def _term(
        self,
        body: Any,
    ) -> str:

        field, value = (
            self._single_field(body)
        )

        if isinstance(value, dict):
            value = value.get("value")

        if value is None:

            raise QueryError(
                f"term value is required: "
                f"{field}"
            )

        return (
            f"{field}:{_quote(value)}"
        )

    # --------------------------------------------------
    # match
    # --------------------------------------------------

    def _match(
        self,
        body: Any,
        size: int,
        offset: int,
    ) -> SearchPlan:

        field, value = (
            self._single_field(body)
        )

        field_type = (
            self.field_type_resolver(
                field
            )
        )

        if field_type.upper() == "VECTOR":

            return self._vector_match(
                field,
                value,
                size=size,
                offset=offset,
            )

        if isinstance(value, dict):

            value = value.get("query")

        if value is None:

            raise QueryError(
                f"match query is required: "
                f"{field}"
            )

        return LexicalSearchPlan(
            f"{field}:{_match_value(value)}"
        )

    def _vector_match(
        self,
        field: str,
        value: Any,
        size: int,
        offset: int,
    ) -> VectorSearchPlan:

        if isinstance(value, str):

            query_text = value

            k = size + offset

            num_candidates = None

            model_id = None

        elif isinstance(value, dict):

            query_text = value.get(
                "query"
            )

            if not query_text:

                raise QueryError(
                    "VECTOR match requires "
                    "'query'"
                )

            k = int(
                value.get(
                    "k",
                    size + offset,
                )
            )

            num_candidates = (
                value.get(
                    "num_candidates"
                )
            )

            model_id = value.get(
                "model_id"
            )

        else:

            raise QueryError(
                "VECTOR match value must "
                "be a string or object"
            )

        minimum_k = size + offset

        if k < minimum_k:

            raise QueryError(
                f"k must be >= "
                f"from + size "
                f"({minimum_k})"
            )

        return VectorSearchPlan(
            field=field,
            query_text=query_text,
            model_id=model_id,
            k=k,
            num_candidates=num_candidates,
        )

    # --------------------------------------------------
    # explicit knn
    # --------------------------------------------------

    def _knn(
        self,
        body: Any,
        size: int,
        offset: int,
    ) -> VectorSearchPlan:

        if not isinstance(body, dict):

            raise QueryError(
                "knn must be an object"
            )

        field = body.get("field")

        if not field:

            raise QueryError(
                "knn.field is required"
            )

        _validate_field(field)

        query_text = body.get(
            "query_text"
        )

        query_vector = body.get(
            "query_vector"
        )

        if (
            query_text is None
        ) == (
            query_vector is None
        ):

            raise QueryError(
                "Specify exactly one of "
                "query_text or query_vector"
            )

        k = int(
            body.get(
                "k",
                size + offset,
            )
        )

        if k < size + offset:

            raise QueryError(
                "k must be >= from + size"
            )

        filter_query = None

        filter_dsl = body.get(
            "filter"
        )

        if filter_dsl:

            filter_query = (
                self._lexical_only(
                    filter_dsl
                )
            )

        return VectorSearchPlan(
            field=field,
            query_text=query_text,
            query_vector=query_vector,
            model_id=body.get(
                "model_id"
            ),
            k=k,
            num_candidates=body.get(
                "num_candidates"
            ),
            filter_query=filter_query,
        )

    # --------------------------------------------------
    # bool
    # --------------------------------------------------

    def _bool(
        self,
        body: Any,
        size: int,
        offset: int,
    ) -> SearchPlan:

        if not isinstance(body, dict):

            raise QueryError(
                "bool must be an object"
            )

        must = self._as_list(
            body.get("must")
        )

        filters = self._as_list(
            body.get("filter")
        )

        must_not = self._as_list(
            body.get("must_not")
        )

        should = self._as_list(
            body.get("should")
        )

        plans = [
            self._build(
                item,
                size=size,
                offset=offset,
            )
            for item in must
        ]

        vector_plans = [
            p
            for p in plans
            if isinstance(
                p,
                VectorSearchPlan,
            )
        ]

        if vector_plans:

            if len(vector_plans) != 1:

                raise UnsupportedQueryError(
                    "Only one VECTOR query "
                    "is supported in bool.must"
                )

            if len(plans) != 1:

                raise UnsupportedQueryError(
                    "Hybrid lexical/vector "
                    "ranking is not supported yet. "
                    "Use bool.filter for lexical "
                    "constraints."
                )

            if should:

                raise UnsupportedQueryError(
                    "bool.should with VECTOR "
                    "search is not supported yet"
                )

            vector_plan = (
                vector_plans[0]
            )

            filter_parts = [
                self._lexical_only(item)
                for item in filters
            ]

            for item in must_not:

                q = self._lexical_only(
                    item
                )

                filter_parts.append(
                    f"NOT ({q})"
                )

            if filter_parts:

                vector_plan.filter_query = (
                    " AND ".join(
                        f"({q})"
                        for q
                        in filter_parts
                    )
                )

            return vector_plan

        #
        # lexical bool
        #

        required = [
            p.lucene_query
            for p in plans
        ]

        required.extend(
            self._lexical_only(item)
            for item in filters
        )

        parts = []

        if required:

            parts.append(
                " AND ".join(
                    f"({q})"
                    for q in required
                )
            )

        if should:

            should_queries = [
                self._lexical_only(item)
                for item in should
            ]

            parts.append(
                "("
                + " OR ".join(
                    f"({q})"
                    for q
                    in should_queries
                )
                + ")"
            )

        for item in must_not:

            q = self._lexical_only(
                item
            )

            if not parts:
                parts.append("*:*")

            parts.append(
                f"NOT ({q})"
            )

        if not parts:
            return LexicalSearchPlan("*:*")

        return LexicalSearchPlan(
            " AND ".join(parts)
        )

    # --------------------------------------------------
    # range
    # --------------------------------------------------

    def _range(
        self,
        body: Any,
    ) -> str:

        field, condition = (
            self._single_field(body)
        )

        if not isinstance(
            condition,
            dict,
        ):

            raise QueryError(
                "range condition must "
                "be an object"
            )

        gt = condition.get("gt")
        gte = condition.get("gte")

        lt = condition.get("lt")
        lte = condition.get("lte")

        if gt is not None and gte is not None:

            raise QueryError(
                "gt and gte cannot both "
                "be specified"
            )

        if lt is not None and lte is not None:

            raise QueryError(
                "lt and lte cannot both "
                "be specified"
            )

        lower = (
            gte
            if gte is not None
            else gt
        )

        upper = (
            lte
            if lte is not None
            else lt
        )

        if lower is None:
            lower = "*"

        if upper is None:
            upper = "*"

        left = (
            "["
            if gt is None
            else "{"
        )

        right = (
            "]"
            if lt is None
            else "}"
        )

        return (
            f"{field}:"
            f"{left}"
            f"{lower} TO {upper}"
            f"{right}"
        )

    # --------------------------------------------------
    # helper
    # --------------------------------------------------

    def _lexical_only(
        self,
        query: dict[str, Any],
    ) -> str:

        plan = self._build(
            query,
            size=10,
            offset=0,
        )

        if not isinstance(
            plan,
            LexicalSearchPlan,
        ):

            raise UnsupportedQueryError(
                "VECTOR query cannot be used "
                "as a lexical filter"
            )

        return plan.lucene_query

    @staticmethod
    def _single_field(
        body: Any,
    ) -> tuple[str, Any]:

        if (
            not isinstance(body, dict)
            or len(body) != 1
        ):

            raise QueryError(
                "Query must contain "
                "exactly one field"
            )

        field, value = next(
            iter(body.items())
        )

        _validate_field(field)

        return field, value

    @staticmethod
    def _as_list(
        value: Any,
    ) -> list[Any]:

        if value is None:
            return []

        if isinstance(value, list):
            return value

        return [value]
