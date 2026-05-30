# SearchEngine クラス
import json
from typing import Any, Iterable, Optional, Sequence

from .errors import InvalidDocumentError, JavaSearchError
from .jvm import ensure_jvm
from .result import SearchResult


class SearchEngine:
    def __init__(
        self,
        lang: str = "ja",
        *,
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
            self._java = LocalSearch(lang)
            self.lang = lang
            self._closed = False
        except Exception as e:
            raise JavaSearchError(f"Failed to create LocalSearch(lang={lang})") from e

    def add(self, id_or_doc: str | dict[str, Any], body: Optional[str] = None) -> None:
        self._ensure_open()

        try:
            if isinstance(id_or_doc, dict):
                self.add_json(id_or_doc)
                return

            if body is None:
                raise InvalidDocumentError("body is required when id is specified")

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

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        self._ensure_open()

        try:
            results = self._java.search(str(query), int(limit))
            return [SearchResult.from_java(r) for r in results]
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