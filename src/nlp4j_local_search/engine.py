# SearchEngine クラス
import json
from typing import Any, Iterable, Optional, Sequence, Union

from .errors import InvalidDocumentError, JavaSearchError
from .jvm import ensure_jvm
from .result import SearchResult


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
        id_or_doc: Union[str, dict[str, Any]],
        body: Optional[Union[str, Sequence[float]]] = None
    ) -> None:
        self._ensure_open()

        try:
            if isinstance(id_or_doc, dict):
                self.add_json(id_or_doc)
                return

            if body is None:
                raise InvalidDocumentError("body is required when id is specified")

            # ベクトル検索の場合
            if isinstance(body, (list, tuple)):
                if self.vector_dimension is None:
                    raise InvalidDocumentError(
                        "vector_dimension must be specified in __init__ to add vectors"
                    )
                vector_array = [float(v) for v in body]
                if len(vector_array) != self.vector_dimension:
                    raise InvalidDocumentError(
                        f"Vector dimension mismatch: expected {self.vector_dimension}, got {len(vector_array)}"
                    )
                self._java.add(str(id_or_doc), vector_array)
            else:
                # テキスト検索の場合
                self._java.add(str(id_or_doc), str(body))

        except InvalidDocumentError:
            raise
        except Exception as e:
            raise JavaSearchError("Failed to add document") from e

    def add_json(self, doc: str | dict[str, Any]) -> None:
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

    def add_all(self, docs: Iterable[dict[str, Any]]) -> None:
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
        limit: int = 10
    ) -> list[SearchResult]:
        self._ensure_open()

        try:
            # ベクトル検索の場合
            if isinstance(query, (list, tuple)):
                if self.vector_dimension is None:
                    raise InvalidDocumentError(
                        "vector_dimension must be specified in __init__ to search with vectors"
                    )
                vector_array = [float(v) for v in query]
                if len(vector_array) != self.vector_dimension:
                    raise InvalidDocumentError(
                        f"Vector dimension mismatch: expected {self.vector_dimension}, got {len(vector_array)}"
                    )
                results = self._java.search(vector_array, int(limit))
            else:
                # テキスト検索の場合
                results = self._java.search(str(query), int(limit))
            
            return [SearchResult.from_java(r) for r in results]
        except InvalidDocumentError:
            raise
        except Exception as e:
            raise JavaSearchError("Failed to search") from e

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