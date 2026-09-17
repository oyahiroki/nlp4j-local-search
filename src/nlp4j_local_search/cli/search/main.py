"""nlp4j-local-search CLI entry point."""
from __future__ import annotations

import argparse
import ast
import sys
import time
from pathlib import Path
from typing import Any, Iterable

from nlp4j_local_search import SearchEngine


HELP_TEXT = """
Commands:

  help
  ?
      Show this help.

  load("file.jsonl")
  load("file.jsonl.gz")
      Load a JSONL dataset and create a searchable local Lucene index.

  load("file.jsonl.gz", embedding="text_ja")
      Load a JSONL dataset and generate vector embeddings from the
      specified field using intfloat/multilingual-e5-large.

      The embedding model is loaded only when embedding is specified.

      Embedding progress is displayed periodically while documents
      are being processed.

      Example:

        load("data.jsonl.gz", embedding="text_ja")

  fields
      Show a summary of fields that contain values.

      Columns:
        Field         Field name
        Type          Field data type
        Aggregatable  Whether the field supports aggregation
        Coverage      Percentage of documents containing a value
        Unique        Number of unique values for KEYWORD fields
        Diversity     Unique / documents containing a value
        Example       Example stored value

      Unique and Diversity are calculated only for aggregatable
      KEYWORD fields.

      Example:

        fields

  aggregatable_fields
      Show fields available for aggregation / view.

  count
      Show the number of loaded documents.

  search("lucene query")
  search("lucene query", limit)
      Search using Lucene Query Parser syntax.

      Examples:

        search("高橋留美子")
        search('"週刊少年サンデー"')
        search('text_ja:"週刊少年サンデー"')
        search("category_s:恋愛漫画")
        search("高橋留美子 AND 星")
        search("text_ja:高橋留美子 AND category_s:恋愛漫画")
        search("timestamp_dt:[2026-01-01 TO *]")

  semantic_search("query")
  semantic_search("query", limit)
      Search by vector similarity.

      Embedding must be enabled when loading the dataset.

      Example:

        load("data.jsonl.gz", embedding="text_ja")
        semantic_search("タイムスリップする恋愛漫画")
        semantic_search("タイムスリップする恋愛漫画", 5)

  view("field")
  view("field", size)
  view("field", size, min_count)
      Show popular values of a field.

      For DATE fields, a yearly histogram is shown by default.

      Examples:

        view("category_s")
        view("category_s", 20)
        view("category_s", 20, 3)

        view("date")
        view("timestamp_dt")

  view("field", "lucene query")
  view("field", "lucene query", size)
  view("field", "lucene query", size, min_count)
      Show values characteristic of documents matching a query.

      For DATE fields, a yearly histogram is shown by default.

      Examples:

        view("category_s", 'text_ja:"高橋留美子"')
        view("category_s", 'text_ja:"高橋留美子"', 20)
        view("category_s", 'text_ja:"高橋留美子"', 20, 3)

        view("date", "Nissan")
        view("timestamp_dt", "Nissan")

  view("date_field", interval="year")
  view("date_field", interval="month")
  view("date_field", interval="hour")
  view("date_field", "lucene query", interval="year")
      Show a date histogram for a DATE field.

      When interval is omitted, "year" is used by default.

      Missing periods are included with count=0.

      DATE fields include:
        - fields ending with "_dt"
        - "date" when its value is ISO 8601
        - explicitly defined DATE fields

      Examples:

        view("date")
        view("date", interval="month")
        view("timestamp_dt")
        view("timestamp_dt", interval="month")
        view("timestamp_dt", "Nissan", interval="year")

  exit
  quit
      Exit the CLI.
""".strip()


class _ProgressEmbeddingProvider:
    """Embedding provider wrapper that reports document progress.

    The wrapped provider still performs all actual embedding work.
    This wrapper only counts completed document embeddings and
    periodically prints progress information.
    """

    def __init__(
        self,
        provider: Any,
        *,
        report_interval_seconds: float = 5.0,
    ) -> None:
        self._provider = provider
        self._report_interval_seconds = report_interval_seconds

        self._processed = 0
        self._started_at: float | None = None
        self._last_report_at: float | None = None

    @property
    def dimension(self) -> int:
        return self._provider.dimension

    def embed_query(self, text: str) -> list[float]:
        return self._provider.embed_query(text)

    def embed_documents(
        self,
        texts: Iterable[str],
    ) -> list[list[float]]:
        batch = list(texts)

        if not batch:
            return self._provider.embed_documents(batch)

        now = time.perf_counter()

        if self._started_at is None:
            self._started_at = now
            self._last_report_at = now

            print(
                "Embedding documents...",
                flush=True,
            )

        vectors = self._provider.embed_documents(batch)

        self._processed += len(batch)

        now = time.perf_counter()

        if (
            self._last_report_at is None
            or now - self._last_report_at
            >= self._report_interval_seconds
        ):
            self._print_progress(now)
            self._last_report_at = now

        return vectors

    def finish(self) -> None:
        """Print the final embedding progress."""
        if self._started_at is None or self._processed == 0:
            return

        now = time.perf_counter()
        elapsed = now - self._started_at
        rate = self._processed / elapsed if elapsed > 0 else 0.0

        print(
            f"Embedding completed: {self._processed:,} documents "
            f"in {elapsed:.1f} seconds "
            f"({rate:,.1f} docs/sec).",
            flush=True,
        )

    def _print_progress(self, now: float) -> None:
        if self._started_at is None:
            return

        elapsed = now - self._started_at
        rate = self._processed / elapsed if elapsed > 0 else 0.0

        print(
            f"Embedding progress: {self._processed:,} documents "
            f"({elapsed:.1f}s, {rate:,.1f} docs/sec)",
            flush=True,
        )


class _LoadProgressReporter:
    """Display load progress on a single terminal line."""

    def __init__(self) -> None:
        self._active = False

    def start(self) -> None:
        print("Loading documents...", flush=True)
        self._active = True

    def update(
        self,
        loaded_count: int,
        elapsed_seconds: float,
    ) -> None:
        rate = (
            loaded_count / elapsed_seconds
            if elapsed_seconds > 0
            else 0.0
        )

        print(
            f"\rLoading: {loaded_count:,} documents "
            f"| {rate:,.0f} docs/sec "
            f"| {elapsed_seconds:.1f}s",
            end="",
            flush=True,
        )

    def finish(self) -> None:
        if self._active:
            print()
            self._active = False


def complete_path(text: str) -> list[str]:
    """Return file-system path completions."""
    path = Path(text).expanduser()

    parent = path.parent
    prefix = path.name

    if str(parent) == ".":
        parent = Path(".")

    try:
        matches: list[str] = []

        for p in parent.iterdir():
            if not p.name.startswith(prefix):
                continue

            value = str(p)

            if p.is_dir():
                value += "/"

            matches.append(value)

        return sorted(matches)

    except OSError:
        return []


def cli_completer(text: str, state: int) -> str | None:
    """Complete file names inside load("...")."""
    import readline  # noqa: PLC0415

    line = readline.get_line_buffer()
    prefix = 'load("'

    if not line.startswith(prefix):
        return None

    path_text = line[len(prefix):]
    matches = complete_path(path_text)

    if state >= len(matches):
        return None

    match = matches[state]

    # Since set_completer_delims("") makes the entire line the
    # completion target, return the complete command prefix as well.
    result = prefix + match

    path = Path(match)

    if path.is_file():
        result += '")'

    return result


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nlp4j-local-search",
        description="Interactive local Lucene search CLI.",
    )

    parser.add_argument(
        "--lang",
        help="Language for text indexing and search, e.g. ja or en.",
    )

    parser.add_argument(
        "--auto-analyze",
        action="store_true",
        help="Enable NLP4J automatic linguistic analysis.",
    )

    parser.add_argument(
        "--time-zone",
        dest="time_zone",
        help='Time zone for DATE fields, e.g. "Asia/Tokyo" or "UTC".',
    )

    return parser


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    if parsed_args.lang is None:
        parser.print_help()
        parser.exit(2)

    return parsed_args


def print_results(results) -> None:
    if not results:
        print("No results.")
        return

    for result in results:
        print(f"[{result.id}] score={result.score:.4f}")

        if result.body:
            print(result.body)

        print()


def parse_function_call(
    line: str,
) -> tuple[str, list[Any], dict[str, Any]]:
    """Parse a restricted function-style CLI command.

    Examples:

        search("Kyoto")
        search("Kyoto", 5)
        load("data.jsonl.gz", embedding="text_ja")

    Only literal positional and keyword arguments are accepted.
    Arbitrary Python expressions are rejected.
    """
    try:
        tree = ast.parse(line, mode="eval")
    except SyntaxError as e:
        raise ValueError("Invalid command syntax.") from e

    if not isinstance(tree.body, ast.Call):
        raise ValueError(
            'Expected a command such as search("Kyoto").'
        )

    call = tree.body

    if not isinstance(call.func, ast.Name):
        raise ValueError("Invalid command.")

    args: list[Any] = []

    for node in call.args:
        try:
            args.append(ast.literal_eval(node))
        except (ValueError, SyntaxError) as e:
            raise ValueError(
                "Arguments must be literal values."
            ) from e

    kwargs: dict[str, Any] = {}

    for kw in call.keywords:
        if kw.arg is None:
            raise ValueError("**kwargs is not supported.")

        try:
            kwargs[kw.arg] = ast.literal_eval(kw.value)
        except (ValueError, SyntaxError) as e:
            raise ValueError(
                "Keyword arguments must be literal values."
            ) from e

    return call.func.id, args, kwargs


class SearchCli:

    def __init__(
        self,
        *,
        lang: str,
        auto_analyze: bool = False,
        time_zone: str | None = None,
    ) -> None:
        self.lang = lang
        self.auto_analyze = auto_analyze
        self.time_zone = time_zone
        self.engine: SearchEngine | None = None
        self.loaded_path: Path | None = None

    def close(self) -> None:
        if self.engine is not None:
            self.engine.close()
            self.engine = None

    def _require_engine(self) -> SearchEngine:
        if self.engine is None:
            raise RuntimeError(
                'No data loaded. Use load("file.jsonl") first.'
            )

        return self.engine

    def _create_embedding(self):
        """Create the optional embedding provider lazily."""
        try:
            from nlp4j_local_search_embedding import E5Embedder
        except ImportError as e:
            raise RuntimeError(
                "Embedding support is not installed. "
                "Install nlp4j-local-search-embedding."
            ) from e

        return E5Embedder(
            model_name="intfloat/multilingual-e5-large",
            show_progress_bar=False,
        )

    def load(
        self,
        path: str,
        *,
        embedding: str | None = None,
    ) -> None:
        path_obj = Path(path).expanduser()

        if not path_obj.exists():
            raise FileNotFoundError(path_obj)

        # Loading another file replaces the current search engine.
        self.close()

        embedder = None
        progress_embedder: _ProgressEmbeddingProvider | None = None

        if embedding is not None:
            print(
                "Loading embedding model: "
                "intfloat/multilingual-e5-large",
                flush=True,
            )

            base_embedder = self._create_embedding()

            progress_embedder = _ProgressEmbeddingProvider(
                base_embedder,
                report_interval_seconds=5.0,
            )

            embedder = progress_embedder

        engine_start = time.perf_counter()

        engine = SearchEngine(
            self.lang,
            auto_analyze=self.auto_analyze,
            embedding=embedder,
            time_zone=self.time_zone,
        )

        if embedding is not None:
            model_elapsed = time.perf_counter() - engine_start

            print(
                f"Embedding model ready "
                f"({model_elapsed:.1f}s).",
                flush=True,
            )

        try:
            start = time.perf_counter()

            pipeline = engine.data(str(path_obj))

            if embedding is not None:
                print(
                    f'Embedding field: "{embedding}"',
                    flush=True,
                )

                pipeline = pipeline.embedding(embedding)

            progress = _LoadProgressReporter()
            progress.start()

            try:
                pipeline.load(
                    progress_callback=progress.update,
                    progress_interval_seconds=1.0,
                )
            finally:
                progress.finish()

            if progress_embedder is not None:
                progress_embedder.finish()

            elapsed = time.perf_counter() - start

            count = engine.count()
            rate = count / elapsed if elapsed > 0 else 0.0

            self.engine = engine
            self.loaded_path = path_obj

            print(
                f"Loaded {count:,} documents "
                f"in {elapsed:.2f} seconds "
                f"({rate:,.0f} docs/sec)."
            )

        except Exception:
            engine.close()
            raise

    def fields(self) -> None:
        engine = self._require_engine()
        print(engine.fields_summary())

    def aggregatable_fields(self) -> None:
        engine = self._require_engine()

        for field in engine.aggregatable_fields():
            print(field)

    def count(self) -> None:
        engine = self._require_engine()
        print(f"{engine.count():,}")

    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> None:
        engine = self._require_engine()

        results = engine.search(
            query,
            limit=int(limit),
        )

        print_results(results)

    def semantic_search(
        self,
        query: str,
        limit: int = 10,
    ) -> None:
        engine = self._require_engine()

        if engine.embedding is None:
            raise RuntimeError(
                "Embedding is not enabled. "
                'Load data with embedding="field".'
            )

        vector = engine.embedding.embed_query(query)

        results = engine.search_vector(
            vector,
            limit=int(limit),
        )

        print_results(results)

    def view(
        self,
        *args: Any,
        interval: str | None = None,
    ) -> None:
        engine = self._require_engine()

        if not args:
            print(engine.view())
            return

        field = args[0]

        if not isinstance(field, str):
            raise ValueError("field must be a string.")

        query: str | None = None
        size: int | None = None
        min_count: int | None = None

        # view("category_s")
        # view("date")
        if len(args) == 1:
            pass

        # view("category_s", 20)
        # view("category_s", "text_ja:高橋留美子")
        # view("date", "Nissan")
        elif len(args) == 2:
            if isinstance(args[1], str):
                query = args[1]
            else:
                size = int(args[1])

        # view("category_s", 20, 3)
        # view("category_s", "query", 20)
        elif len(args) == 3:
            if isinstance(args[1], str):
                query = args[1]
                size = int(args[2])
            else:
                size = int(args[1])
                min_count = int(args[2])

        # view("category_s", "query", 20, 3)
        elif len(args) == 4:
            if not isinstance(args[1], str):
                raise ValueError(
                    "The second argument must be a Lucene query string."
                )

            query = args[1]
            size = int(args[2])
            min_count = int(args[3])

        else:
            raise ValueError(
                "view() accepts at most four arguments."
            )

        if interval is not None:
            # DATE histogram interval is explicitly specified.
            # size is intentionally not passed because DATE histogram
            # does not use the normal terms-aggregation size.
            result = engine.view(
                field,
                query,
                interval=interval,
            )
        else:
            # SearchEngine determines whether the field is a DATE field.
            # DATE fields automatically use interval="year".
            # Normal fields use the default size when size is None.
            result = engine.view(
                field,
                query,
                size=size,
            )

        if min_count is not None:
            result = result.filter(
                min_count=min_count,
            )

        print(result)

    def execute(self, line: str) -> bool:
        line = line.strip()

        if not line:
            return True

        lower = line.lower()

        if lower in {"exit", "quit"}:
            return False

        if lower in {"help", "?"}:
            print(HELP_TEXT)
            return True

        if lower in {"fields", "fields()"}:
            self.fields()
            return True

        if lower in {
            "aggregatable_fields",
            "aggregatable_fields()",
        }:
            self.aggregatable_fields()
            return True

        if lower in {"count", "count()"}:
            self.count()
            return True

        name, args, kwargs = parse_function_call(line)

        if name == "load":

            if len(args) != 1 or not isinstance(args[0], str):
                raise ValueError(
                    'Usage: load("file.jsonl", embedding="text_ja")'
                )

            unknown = set(kwargs) - {"embedding"}

            if unknown:
                raise ValueError(
                    f"Unknown load options: {sorted(unknown)}"
                )

            embedding = kwargs.get("embedding")

            if embedding is not None:
                if (
                    not isinstance(embedding, str)
                    or not embedding.strip()
                ):
                    raise ValueError(
                        "embedding must be a non-empty field name."
                    )

            self.load(
                args[0],
                embedding=embedding,
            )

        elif name == "search":

            if kwargs:
                raise ValueError(
                    "search() does not accept keyword arguments."
                )

            if not 1 <= len(args) <= 2:
                raise ValueError(
                    'Usage: search("query", [limit])'
                )

            query = args[0]

            if not isinstance(query, str):
                raise ValueError(
                    "query must be a string."
                )

            limit = 10 if len(args) == 1 else int(args[1])

            if limit <= 0:
                raise ValueError(
                    "limit must be greater than zero."
                )

            self.search(
                query,
                limit,
            )

        elif name == "semantic_search":

            if kwargs:
                raise ValueError(
                    "semantic_search() does not accept "
                    "keyword arguments."
                )

            if not 1 <= len(args) <= 2:
                raise ValueError(
                    'Usage: semantic_search("query", [limit])'
                )

            query = args[0]

            if not isinstance(query, str):
                raise ValueError(
                    "query must be a string."
                )

            limit = 10 if len(args) == 1 else int(args[1])

            if limit <= 0:
                raise ValueError(
                    "limit must be greater than zero."
                )

            self.semantic_search(
                query,
                limit,
            )

        elif name == "view":

            unknown = set(kwargs) - {"interval"}

            if unknown:
                raise ValueError(
                    f"Unknown view options: {sorted(unknown)}"
                )

            interval = kwargs.get("interval")

            if interval is not None:
                if (
                    not isinstance(interval, str)
                    or not interval.strip()
                ):
                    raise ValueError(
                        "interval must be a non-empty string."
                    )

            self.view(
                *args,
                interval=interval,
            )

        else:
            raise ValueError(
                f"Unknown command: {name}. "
                "Type 'help' for available commands."
            )

        return True


def repl(cli: SearchCli) -> None:
    import readline  # noqa: PLC0415

    readline.set_completer(cli_completer)
    readline.parse_and_bind("tab: complete")

    # Treat the entire command line as the completion target.
    readline.set_completer_delims("")

    print("nlp4j-local-search")
    print(f"Language: {cli.lang}")
    print(f"Auto analyze: {cli.auto_analyze}")

    if cli.time_zone is not None:
        print(f"Time zone: {cli.time_zone}")

    print("Type 'help' or '?' for help.")
    print()

    while True:
        try:
            line = input(">> ")

            if not cli.execute(line):
                print("bye")
                break

        except EOFError:
            print()
            print("bye")
            break

        except KeyboardInterrupt:
            print()
            continue

        except Exception as e:
            print(f"Error: {e}")


def main(args: list[str] | None = None) -> int:
    parsed_args = parse_args(args)

    cli = SearchCli(
        lang=parsed_args.lang,
        auto_analyze=parsed_args.auto_analyze,
        time_zone=parsed_args.time_zone,
    )

    try:
        repl(cli)
    finally:
        cli.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())