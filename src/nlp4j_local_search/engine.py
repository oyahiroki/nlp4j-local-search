# SearchEngine クラス
import json
from collections.abc import Mapping, Sequence
from typing import Any, Iterable, Optional, Union

from jpype import JArray, JFloat

from .errors import InvalidDocumentError, JavaSearchError
from .jvm import ensure_jvm
from .result import SearchResult

# フィールド絞り込み用の型エイリアス
# 登録フィールド値: str または list[str]
KeywordValue = Union[str, "list[str]"]
DocumentFields = Mapping[str, KeywordValue]

# 検索時フィルター値は単一値のみ
FilterMap = Mapping[str, str]

# aggregate_json / search_json / search_response_json の引数型
JsonRequest = Union[str, Mapping[str, Any]]

# add()/search() の fields/filters に使用できない予約済みフィールド名
_RESERVED_FIELDS = frozenset({"id", "body", "vector"})


# ---------------------------------------------------------------------------
# JSON 変換ヘルパー
# ---------------------------------------------------------------------------

def _to_json_text(value: JsonRequest, *, argument_name: str) -> str:
    """Mapping または JSON 文字列を JSON 文字列へ変換する。"""
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        try:
            return json.dumps(dict(value), ensure_ascii=False)
        except (TypeError, ValueError) as e:
            raise InvalidDocumentError(
                f"{argument_name} is not JSON serializable"
            ) from e

    raise InvalidDocumentError(
        f"{argument_name} must be a mapping or JSON string"
    )


def _parse_json_response(value: Any, *, operation_name: str) -> "dict[str, Any]":
    """Java から返された文字列を dict へパースする。"""
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError) as e:
        raise JavaSearchError(
            f"{operation_name} returned invalid JSON"
        ) from e

    if not isinstance(parsed, dict):
        raise JavaSearchError(
            f"{operation_name} response must be a JSON object"
        )

    return parsed


def _to_java_string_map(values: Optional[FilterMap], *, argument_name: str):
    """Python の dict を Java の HashMap<String, String> へ変換する。

    None または空の場合は None を返す。
    """
    if not values:
        return None

    from java.util import HashMap  # noqa: PLC0415 (遅延インポート: JVM 起動後に呼ばれる)

    java_map = HashMap()
    for field_name, field_value in values.items():
        if not isinstance(field_name, str) or not field_name:
            raise InvalidDocumentError(
                f"{argument_name} field names must be non-empty strings"
            )
        if not isinstance(field_value, str):
            raise InvalidDocumentError(
                f"{argument_name}[{field_name!r}] must be a string"
            )
        java_map.put(field_name, field_value)

    return java_map


class SearchEngine:
    def __init__(
        self,
        lang: str = "ja",
        *,
        vector_dimension: Optional[int] = None,
        classpath: Optional[Sequence[str]] = None,
        jvm_args: Optional[Sequence[str]] = None,
    ) -> None:
        ensure_jvm(classpath=classpath, jvm_args=jvm_args)

        try:
            from nlp4j.lucene import LocalSearch
        except Exception as e:
            raise JavaSearchError(
                "Failed to import Java class: nlp4j.lucene.LocalSearch"
            ) from e

        try:
            if vector_dimension is not None:
                self._java = LocalSearch(lang, int(vector_dimension))
                self.vector_dimension = vector_dimension
            else:
                self._java = LocalSearch(lang)
                self.vector_dimension = None
            self.lang = lang
            self._closed = False
        except Exception as e:
            raise JavaSearchError(f"Failed to create LocalSearch(lang={lang})") from e

    def add(
        self,
        id_or_doc: Union[str, "dict[str, Any]"],
        body: Optional[Union[str, Sequence[float]]] = None,
        *,
        fields: Optional[FilterMap] = None,
    ) -> None:
        """ドキュメントをインデックスへ追加する。

        テキスト検索:
            add("1", "本文テキスト")
            add("1", "本文テキスト", fields={"category": "city"})

        ベクトル検索:
            add("1", [1.0, 0.0])
            add("1", [1.0, 0.0], fields={"category": "tech"})

        dict 登録 (add_json へ委譲):
            add({"id": "1", "body": "...", "category": "city"})
        """
        self._ensure_open()

        try:
            if isinstance(id_or_doc, dict):
                if fields:
                    raise InvalidDocumentError(
                        "fields cannot be used when id_or_doc is already a dict"
                    )
                self.add_json(id_or_doc)
                return

            if body is None:
                raise InvalidDocumentError("body is required when id is specified")

            # fields の予約語チェック
            if fields:
                conflicts = _RESERVED_FIELDS.intersection(fields.keys())
                if conflicts:
                    raise InvalidDocumentError(
                        f"reserved field names cannot be used: {sorted(conflicts)}"
                    )

            # ベクトル文書
            if isinstance(body, (list, tuple)):
                if self.vector_dimension is None:
                    raise InvalidDocumentError(
                        "vector_dimension must be specified in __init__ to add vectors"
                    )
                vector_values = [float(v) for v in body]
                if len(vector_values) != self.vector_dimension:
                    raise InvalidDocumentError(
                        f"Vector dimension mismatch: expected {self.vector_dimension}, "
                        f"got {len(vector_values)}"
                    )
                # JPype のオーバーロード解決を安定させるため float[] を明示生成
                vector_array = JArray(JFloat)(vector_values)
                java_fields = _to_java_string_map(fields, argument_name="fields")

                if java_fields is None:
                    self._java.add(str(id_or_doc), vector_array)
                else:
                    self._java.add(str(id_or_doc), vector_array, java_fields)

            # テキスト文書
            else:
                if fields:
                    # add_json 経由で追加フィールドをまとめて登録する
                    document = {
                        "id": str(id_or_doc),
                        "body": str(body),
                        **dict(fields),
                    }
                    self.add_json(document)
                else:
                    self._java.add(str(id_or_doc), str(body))

        except InvalidDocumentError:
            raise
        except Exception as e:
            raise JavaSearchError("Failed to add document") from e

    def add_json(self, doc: Union[str, "dict[str, Any]"]) -> None:
        """JSON ドキュメントをインデックスへ追加する。

        タグなど複数値（JSON配列）を持つ MultiValued フィールドも使用できる。

        例:
            add_json({"id": "1", "body": "...", "tags": ["city", "Japan"]})
        """
        self._ensure_open()

        if isinstance(doc, dict):
            json_text = json.dumps(doc, ensure_ascii=False)
        elif isinstance(doc, str):
            json_text = doc
        else:
            raise InvalidDocumentError("doc must be dict or JSON string")

        try:
            self._java.addJson(json_text)
        except Exception as e:
            raise JavaSearchError("Failed to add JSON document") from e

    def add_all(self, docs: Iterable["dict[str, Any]"]) -> None:
        for doc in docs:
            self.add_json(doc)

    def commit(self) -> None:
        self._ensure_open()

        try:
            self._java.commit()
        except Exception as e:
            raise JavaSearchError("Failed to commit index") from e

    def search(
        self,
        query: Union[str, Sequence[float]],
        limit: int = 10,
        *,
        filters: Optional[FilterMap] = None,
    ) -> "list[SearchResult]":
        """インデックスを検索する。

        テキスト検索:
            search("京都", limit=10)
            search("京都", limit=10, filters={"category": "city"})
            search("", limit=10, filters={"country": "Japan"})  # match_all + フィールド絞り込み

        ベクトル検索:
            search([0.9, 0.1], limit=10)
            search([0.9, 0.1], limit=10, filters={"category": "tech"})

        filters は複数指定した場合、すべて AND 条件になります。
        フィールド値は keyword 完全一致（term クエリ）です。
        MultiValued フィールド（JSON 配列）も単一値フィルターで絞り込めます。
        同一フィールドに対する複数値 AND 条件は search_response_json() を使用してください。
        """
        self._ensure_open()

        if limit < 1:
            raise InvalidDocumentError("limit must be greater than 0")

        try:
            java_filters = _to_java_string_map(filters, argument_name="filters")

            # ベクトル検索
            if isinstance(query, (list, tuple)):
                if self.vector_dimension is None:
                    raise InvalidDocumentError(
                        "vector_dimension must be specified in __init__ to search with vectors"
                    )
                vector_values = [float(v) for v in query]
                if len(vector_values) != self.vector_dimension:
                    raise InvalidDocumentError(
                        f"Vector dimension mismatch: expected {self.vector_dimension}, "
                        f"got {len(vector_values)}"
                    )
                vector_array = JArray(JFloat)(vector_values)

                if java_filters is None:
                    java_results = self._java.search(vector_array, int(limit))
                else:
                    java_results = self._java.search(vector_array, int(limit), java_filters)

            # キーワード検索
            elif isinstance(query, str):
                if java_filters is None:
                    java_results = self._java.search(query, int(limit))
                else:
                    java_results = self._java.search(query, int(limit), java_filters)

            else:
                raise InvalidDocumentError(
                    "query must be a string or a sequence of floats"
                )

            return [SearchResult.from_java(r) for r in java_results]

        except InvalidDocumentError:
            raise
        except Exception as e:
            raise JavaSearchError("Failed to search") from e

    def search_json(
        self,
        request: JsonRequest,
    ) -> "list[SearchResult]":
        """OpenSearch Query DSL を直接指定して検索し、SearchResult のリストを返す。

        例:
            results = engine.search_json({
                "size": 10,
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"tags": "Japan"}},
                            {"term": {"tags": "city"}},
                        ]
                    }
                },
            })
        """
        self._ensure_open()

        request_text = _to_json_text(request, argument_name="request")

        try:
            java_results = self._java.searchJson(request_text)
            return [SearchResult.from_java(r) for r in java_results]
        except Exception as e:
            raise JavaSearchError("Failed to execute JSON search") from e

    def search_response_json(
        self,
        request: JsonRequest,
    ) -> "dict[str, Any]":
        """OpenSearch Query DSL を直接指定して検索し、OpenSearch 形式の dict を返す。

        hits / aggregations / total など完全なレスポンスが得られます。
        同一フィールドへの複数値 AND 条件にも使用できます。

        例:
            response = engine.search_response_json({
                "size": 10,
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"tags": "Japan"}},
                            {"term": {"tags": "city"}},
                        ]
                    }
                },
            })
            total = response["hits"]["total"]["value"]
            for hit in response["hits"]["hits"]:
                print(hit["_source"]["id"])
        """
        self._ensure_open()

        request_text = _to_json_text(request, argument_name="request")

        try:
            response_text = self._java.searchResponseJson(request_text)
            return _parse_json_response(response_text, operation_name="searchResponseJson")
        except JavaSearchError:
            raise
        except Exception as e:
            raise JavaSearchError("Failed to execute JSON search response") from e

    def aggregate_json(
        self,
        request: JsonRequest,
    ) -> "dict[str, Any]":
        """Java の aggregateJson() を直接呼び出す低レベル API。

        レスポンスは OpenSearch aggregation 形式の dict です。

        例:
            response = engine.aggregate_json({
                "name": "tags",
                "field": "tags",
                "size": 10,
                "query": "Kyoto",
            })
            for bucket in response["aggregations"]["tags"]["buckets"]:
                print(bucket["key"], bucket["doc_count"])
        """
        self._ensure_open()

        request_text = _to_json_text(request, argument_name="request")

        try:
            response_text = self._java.aggregateJson(request_text)
            return _parse_json_response(response_text, operation_name="aggregateJson")
        except JavaSearchError:
            raise
        except Exception as e:
            raise JavaSearchError("Failed to aggregate") from e

    def aggregate(
        self,
        field: str,
        *,
        name: Optional[str] = None,
        size: int = 10,
        query: Optional[str] = None,
        filters: Optional[FilterMap] = None,
    ) -> "dict[str, Any]":
        """terms aggregation を実行する Python 向け高レベル API。

        戻り値は OpenSearch aggregation 形式の dict です。

        例:
            response = engine.aggregate("tags", size=10, query="Kyoto")
            for bucket in response["aggregations"]["tags"]["buckets"]:
                print(bucket["key"], bucket["doc_count"])

        Args:
            field:   集計対象のフィールド名。
            name:    集計名（省略時は field と同じ）。
            size:    返すバケット数の上限。
            query:   全文検索による事前絞り込みクエリ（省略可）。
            filters: フィールド絞り込み条件（省略可）。
        """
        if not isinstance(field, str) or not field:
            raise InvalidDocumentError("field must be a non-empty string")

        if size < 1:
            raise InvalidDocumentError("size must be greater than 0")

        request: "dict[str, Any]" = {
            "name": name or field,
            "field": field,
            "size": size,
        }

        if query:
            request["query"] = query

        if filters:
            request["filters"] = dict(filters)

        return self.aggregate_json(request)

    def close(self) -> None:
        if self._closed:
            return

        try:
            self._java.close()
        finally:
            self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise JavaSearchError("SearchEngine is already closed")

    def __enter__(self) -> "SearchEngine":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
