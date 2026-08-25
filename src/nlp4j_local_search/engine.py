# SearchEngine クラス
import json
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Iterable, Optional, Union

from jpype import JArray, JFloat

from .analytics import AnalyticsResult
from .errors import InvalidDocumentError, JavaSearchError
from .jvm import ensure_jvm
from .result import SearchResult
from .view import ViewBucket, ViewField, ViewResult

if TYPE_CHECKING:
    from .embedding import EmbeddingProvider
    from .data import DataPipeline

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
        auto_analyze: bool = True,
        vector_dimension: Optional[int] = None,
        embedding: "Optional[EmbeddingProvider]" = None,
        classpath: Optional[Sequence[str]] = None,
        jvm_args: Optional[Sequence[str]] = None,
    ) -> None:
        # Resolve vector_dimension from embedding if provided
        if embedding is not None:
            if vector_dimension is None:
                vector_dimension = embedding.dimension
            elif vector_dimension != embedding.dimension:
                raise ValueError(
                    "vector_dimension does not match embedding.dimension"
                )

        ensure_jvm(classpath=classpath, jvm_args=jvm_args)

        try:
            from nlp4j.lucene import LocalSearch

            builder = LocalSearch.builder(lang)
            builder = builder.autoAnalyze(bool(auto_analyze))

            if vector_dimension is not None:
                builder = builder.vectorDimension(int(vector_dimension))

            self._java = builder.build()
            self.lang = lang
            self.auto_analyze = auto_analyze
            self.vector_dimension = vector_dimension
            self.embedding: "Optional[EmbeddingProvider]" = embedding
            self._analytics = None
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
        query: str,
        limit: int = 10,
    ) -> "list[SearchResult]":
        """Lucene Query Syntax でインデックスを検索する。

        Java の ``searchLucene(query, limit)`` を呼び出す。
        Lucene のクエリ構文をそのまま使用できる正式 API。

        テキストフィールドの内部名::

            "ja" エンジン → text_ja
            "en" エンジン → text_en

        クエリ例::

            # bare term（デフォルトフィールドで検索）
            engine.search("京都")
            engine.search("Kyoto")

            # フィールド指定
            engine.search("text_en:Kyoto")
            engine.search("text_ja:京都")

            # AND / OR / NOT
            engine.search("text_en:Kyoto AND text_en:historic")
            engine.search("text_en:Kyoto OR text_en:Tokyo")
            engine.search("category:city AND NOT country:Japan")

            # keyword フィールド完全一致
            engine.search("category:city")
            engine.search("category:city AND country:Japan")

            # ワイルドカード
            engine.search("text_en:Kyo*")

            # フレーズ検索
            engine.search('text_en:"historic city"')

            # 数値レンジ (スキーマに integer/double フィールドが必要)
            engine.search("year_i:[2025 TO 2026]")

        ベクトル検索は :meth:`search_vector` を使用してください。

        Args:
            query:  Lucene クエリ文字列。
            limit:  返す件数の上限（1 以上）。

        Returns:
            :class:`~nlp4j_local_search.result.SearchResult` のリスト。

        Raises:
            :class:`~nlp4j_local_search.errors.InvalidDocumentError`:
                *limit* が 1 未満のとき。
            :class:`~nlp4j_local_search.errors.JavaSearchError`:
                Java 層でエラーが発生したとき。
        """
        self._ensure_open()

        if not isinstance(query, str):
            raise InvalidDocumentError("query must be a string")

        if limit < 1:
            raise InvalidDocumentError("limit must be greater than 0")

        try:
            java_results = self._java.searchLucene(query, int(limit))
            return [SearchResult.from_java(r) for r in java_results]

        except InvalidDocumentError:
            raise
        except Exception as e:
            raise JavaSearchError("Failed to search") from e

    def search_vector(
        self,
        vector: Sequence[float],
        limit: int = 10,
        *,
        filters: Optional[FilterMap] = None,
    ) -> "list[SearchResult]":
        """ベクトル検索を実行する。

        クエリベクトルとのコサイン類似度が高い順に結果を返す。

        例::

            # フィルターなし
            engine.search_vector([0.9, 0.1], limit=10)

            # keyword フィールドで絞り込み（AND 結合）
            engine.search_vector([0.9, 0.1], limit=10, filters={"category": "tech"})
            engine.search_vector([0.9, 0.1], limit=10,
                                 filters={"category": "tech", "country": "Japan"})

        Args:
            vector:  クエリベクトル（float のシーケンス）。
            limit:   返す件数の上限（1 以上）。
            filters: keyword フィールドの絞り込み条件（省略可）。

        Returns:
            :class:`~nlp4j_local_search.result.SearchResult` のリスト。

        Raises:
            :class:`~nlp4j_local_search.errors.InvalidDocumentError`:
                *vector_dimension* 未設定・次元数不一致・*limit* < 1 のとき。
            :class:`~nlp4j_local_search.errors.JavaSearchError`:
                Java 層でエラーが発生したとき。
        """
        self._ensure_open()

        if limit < 1:
            raise InvalidDocumentError("limit must be greater than 0")

        if self.vector_dimension is None:
            raise InvalidDocumentError(
                "vector_dimension must be specified in __init__ to search with vectors"
            )

        try:
            vector_values = [float(v) for v in vector]
            if len(vector_values) != self.vector_dimension:
                raise InvalidDocumentError(
                    f"Vector dimension mismatch: expected {self.vector_dimension}, "
                    f"got {len(vector_values)}"
                )
            vector_array = JArray(JFloat)(vector_values)
            java_filters = _to_java_string_map(filters, argument_name="filters")

            if java_filters is None:
                java_results = self._java.search(vector_array, int(limit))
            else:
                java_results = self._java.search(vector_array, int(limit), java_filters)

            return [SearchResult.from_java(r) for r in java_results]

        except InvalidDocumentError:
            raise
        except Exception as e:
            raise JavaSearchError("Failed to search vectors") from e

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
        lucene_query: Optional[str] = None,
        filters: Optional[FilterMap] = None,
    ) -> "dict[str, Any]":
        """terms aggregation を実行する Python 向け高レベル API。

        戻り値は OpenSearch aggregation 形式の dict です。

        例:
            response = engine.aggregate("tags", size=10, query="Kyoto")
            for bucket in response["aggregations"]["tags"]["buckets"]:
                print(bucket["key"], bucket["doc_count"])

        Args:
            field:        集計対象のフィールド名。
            name:         集計名（省略時は field と同じ）。
            size:         返すバケット数の上限。
            query:        全文検索による事前絞り込みクエリ（省略可）。
            lucene_query: Lucene 構文クエリによる事前絞り込み（省略可）。
                          full-text フィールド（text_en, text_ja など）を対象にする。
                          例: "text_en:Kyoto AND text_en:historic"
            filters:      フィールド絞り込み条件（省略可）。
        """
        if not isinstance(field, str) or not field:
            raise InvalidDocumentError("field must be a non-empty string")

        if size < 1:
            raise InvalidDocumentError("size must be greater than 0")

        if query is not None and lucene_query is not None:
            raise InvalidDocumentError(
                "query and lucene_query cannot be used together"
            )

        request: "dict[str, Any]" = {
            "name": name or field,
            "field": field,
            "size": size,
        }

        if query:
            request["query"] = query

        if lucene_query:
            request["lucene_query"] = lucene_query

        if filters:
            request["filters"] = dict(filters)

        return self.aggregate_json(request)

    def fields(self) -> "list[str]":
        """インデックスに登録されているすべてのフィールド名を返す。

        例:
            print(engine.fields())
            # ['id', 'body', 'word.noun', 'word.verb', 'category', ...]
        """
        self._ensure_open()

        try:
            java_fields = self._java.getFields()
            return [str(f) for f in java_fields]
        except Exception as e:
            raise JavaSearchError("Failed to get fields") from e

    def aggregatable_fields(self) -> "list[str]":
        """terms aggregation が可能なフィールド名の一覧を返す。

        例:
            print(engine.aggregatable_fields())
            # ['word.noun', 'word.verb', 'category', ...]
        """
        self._ensure_open()

        try:
            java_fields = self._java.getAggregatableFields()
            return [str(f) for f in java_fields]
        except Exception as e:
            raise JavaSearchError("Failed to get aggregatable fields") from e

    def relative_rate_lucene(
        self,
        lucene_query: str,
        field: str,
        *,
        candidate_size: int = 1000,
    ) -> AnalyticsResult:
        """Lucene クエリで絞り込んだ文書集合について relativeRate を返す。

        keyword フィールド（maker, category など）も対象にできる。

        例:
            result = engine.relative_rate_lucene(
                "maker:Nissan",
                "part",
                candidate_size=1000,
            )
            for bucket in result.buckets:
                print(bucket.key, bucket.relative_rate)

        Args:
            lucene_query:   Lucene 構文クエリ（keyword フィールドも指定可）。
            field:          集計対象フィールド名。
            candidate_size: relativeRate 計算の候補数上限。
        """
        self._ensure_open()

        if not lucene_query:
            raise InvalidDocumentError("lucene_query must be a non-empty string")

        if not field:
            raise InvalidDocumentError("field must be a non-empty string")

        if candidate_size < 1:
            raise InvalidDocumentError("candidate_size must be greater than 0")

        try:
            analytics = self._get_analytics()
            java_result = analytics.relativeRateLucene(
                lucene_query,
                field,
                int(candidate_size),
            )
            return AnalyticsResult.from_java(java_result)

        except InvalidDocumentError:
            raise
        except Exception as e:
            raise JavaSearchError("Failed to execute relativeRateLucene") from e

    def _view_field(
        self,
        field: str,
        *,
        size: int,
        lucene_query: Optional[str],
        candidate_size: int,
    ) -> ViewField:
        """単一フィールドの集計を実行して ViewField を返す内部ヘルパー。

        lucene_query なし → aggregate() → count のみ
        lucene_query あり → relative_rate_lucene() → count / all_count / relative_rate
        """
        if lucene_query is None:
            response = self.aggregate(field, size=size)
            agg_name = field
            buckets_raw = (
                response
                .get("aggregations", {})
                .get(agg_name, {})
                .get("buckets", [])
            )
            return ViewField(
                field=field,
                buckets=[
                    ViewBucket(
                        key=b["key"],
                        count=int(b["doc_count"]),
                    )
                    for b in buckets_raw
                ],
            )
        else:
            analytics_result = self.relative_rate_lucene(
                lucene_query,
                field,
                candidate_size=candidate_size,
            )
            buckets = [
                ViewBucket(
                    key=b.key,
                    count=b.count,
                    all_count=b.all_count,
                    relative_rate=b.relative_rate,
                )
                for b in analytics_result.buckets[:size]
            ]
            return ViewField(
                field=field,
                buckets=buckets,
                count=analytics_result.count,
                total_count=analytics_result.total_count,
            )

    def view(
        self,
        field: Optional[str] = None,
        lucene_query: Optional[str] = None,
        *,
        size: Optional[int] = None,
        candidate_size: int = 1000,
    ) -> ViewResult:
        """インデックスのデータをひと目で概観するための inspection API。

        引数なし:
            engine.view()
            → aggregatable な全フィールドの count 上位3件。

        フィールド指定:
            engine.view("category")
            → category フィールドの count 上位10件（縦型テーブル）。

        Lucene クエリで絞り込み:
            engine.view("part", "maker:Nissan")
            → maker:Nissan 対象の part について relativeRate 上位10件。
            engine.view(lucene_query="maker:Nissan")
            → 全 aggregatable フィールドについて relativeRate 上位3件。

        size / candidate_size 指定:
            engine.view("part", "maker:Nissan", size=20, candidate_size=1000)
            → 最大1000候補で統計計算し、上位20件を表示。

        チェーン操作:
            engine.view("part", "maker:Nissan") \\
                .filter(min_relative_rate=1.5) \\
                .sort_by("relative_rate")

        戻り値は ViewResult。print() または repr() で整形表示される。
        Jupyter / Colab では式として評価するだけでも表示される。
        """
        self._ensure_open()

        if size is None:
            size = 3 if field is None else 10

        if size < 1:
            raise InvalidDocumentError("size must be greater than 0")

        if candidate_size < 1:
            raise InvalidDocumentError("candidate_size must be greater than 0")

        sort_key: str = "relative_rate" if lucene_query else "count"

        if field is not None:
            item = self._view_field(
                field,
                size=size,
                lucene_query=lucene_query,
                candidate_size=candidate_size,
            )
            return ViewResult(
                fields=[item],
                lucene_query=lucene_query,
                single_field=True,
                sort_key=sort_key,
            )

        # 全 aggregatable field を取得
        items: "list[ViewField]" = []
        for field_name in self.aggregatable_fields():
            item = self._view_field(
                field_name,
                size=size,
                lucene_query=lucene_query,
                candidate_size=candidate_size,
            )
            if item.buckets:
                items.append(item)

        return ViewResult(
            fields=items,
            lucene_query=lucene_query,
            sort_key=sort_key,
        )

    def relative_rate(
        self,
        query_field: str,
        query_value: str,
        field: str,
        *,
        size: int = 100,
    ) -> AnalyticsResult:
        """フィールド値で絞り込んだ文書集合について、特徴的な語のrelativeRateを返す。

        例:
            result = engine.relative_rate(
                query_field="word.noun",
                query_value="ニッサン",
                field="word.noun",
                size=100,
            )
            for bucket in result.buckets:
                print(bucket.key, bucket.relative_rate)
        """
        self._ensure_open()

        if not query_field:
            raise InvalidDocumentError("query_field must be a non-empty string")

        if query_value is None:
            raise InvalidDocumentError("query_value must not be None")

        if not field:
            raise InvalidDocumentError("field must be a non-empty string")

        if size < 1:
            raise InvalidDocumentError("size must be greater than 0")

        try:
            analytics = self._get_analytics()

            java_result = analytics.relativeRate(
                query_field,
                query_value,
                field,
                int(size),
            )

            return AnalyticsResult.from_java(java_result)

        except InvalidDocumentError:
            raise

        except Exception as e:
            raise JavaSearchError("Failed to execute text analytics") from e

    def _get_analytics(self):
        """LocalAnalytics を遅延生成して返す。"""
        if self._analytics is not None:
            return self._analytics

        try:
            from nlp4j.analytics import LocalAnalytics

            self._analytics = LocalAnalytics(self._java)
            return self._analytics

        except Exception as e:
            raise JavaSearchError("Failed to create LocalAnalytics") from e

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

    def data(self, path: str) -> "DataPipeline":
        """Create a :class:`~nlp4j_local_search.data.DataPipeline` for *path*.

        Supports JSONL files.  Fluent transforms can be chained before
        calling :meth:`~nlp4j_local_search.data.DataPipeline.load`::

            result = (
                engine.data("test.jsonl")
                      .remove("xxx")
                      .rename("category", "category_s")
                      .embedding("text_en")
                      .save_as("out.jsonl")
                      .load()
            )
        """
        from .data import DataPipeline
        return DataPipeline.from_jsonl(path, engine=self)

    def __enter__(self) -> "SearchEngine":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
