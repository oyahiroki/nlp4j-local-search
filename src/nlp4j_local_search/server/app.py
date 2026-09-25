from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
)

from nlp4j_local_search import SearchEngine

from .models import (
    CountRequest,
    SearchRequest,
)

from .query import (
    QueryError,
    UnsupportedQueryError,
)

from .service import (
    SearchService,
    ServerConfig,
)


def create_app(
    config: ServerConfig | None = None,
) -> FastAPI:

    if config is None:
        config = ServerConfig()

    holder = {}

    @asynccontextmanager
    async def lifespan(
        app: FastAPI,
    ):

        engine = SearchEngine(
            lang=config.lang,
            auto_analyze=(
                config.auto_analyze
            ),
        )

        if config.data_path:

            engine.data(
                config.data_path
            ).load()

        holder["service"] = (
            SearchService(
                engine=engine,
                index_name=(
                    config.index_name
                ),
            )
        )

        try:

            yield

        finally:

            holder.clear()

            close = getattr(
                engine,
                "close",
                None,
            )

            if close:
                close()

    app = FastAPI(
        title=(
            "NLP4J Local Search "
            "REST API"
        ),
        description=(
            "Elasticsearch/OpenSearch-style "
            "REST API for NLP4J Local Search"
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    def service() -> SearchService:

        return holder["service"]

    def check_index(
        index: str,
    ):

        try:

            service().check_index(
                index
            )

        except KeyError:

            raise HTTPException(
                status_code=404,
                detail={
                    "type":
                    "index_not_found_exception",
                    "reason":
                    f"no such index "
                    f"[{index}]",
                },
            )

    # --------------------------------------------
    # root
    # --------------------------------------------

    @app.get("/")
    def root():

        return {
            "name":
            "nlp4j-local-search",
            "cluster_name":
            "nlp4j-local-search",
            "version": {
                "distribution":
                "nlp4j-local-search",
            },
            "tagline":
            "Local Lucene search "
            "with NLP4J",
        }

    # --------------------------------------------
    # search GET
    # --------------------------------------------

    @app.get(
        "/{index}/_search"
    )
    def search_get(
        index: str,
        q: str | None = None,
        size: int = Query(
            default=10,
            ge=0,
        ),
        offset: int = Query(
            default=0,
            alias="from",
            ge=0,
        ),
    ):

        check_index(index)

        query = None

        if q:

            query = {
                "query_string": {
                    "query": q
                }
            }

        request = SearchRequest(
            query=query,
            size=size,
            **{"from": offset},
        )

        return run_search(
            service(),
            request,
        )

    # --------------------------------------------
    # search POST
    # --------------------------------------------

    @app.post(
        "/{index}/_search"
    )
    def search_post(
        index: str,
        request: SearchRequest,
    ):

        check_index(index)

        return run_search(
            service(),
            request,
        )

    # --------------------------------------------
    # count
    # --------------------------------------------

    @app.get(
        "/{index}/_count"
    )
    def count_get(
        index: str,
        q: str | None = None,
    ):

        check_index(index)

        query = None

        if q:

            query = {
                "query_string": {
                    "query": q
                }
            }

        return run_count(
            service(),
            query,
        )

    @app.post(
        "/{index}/_count"
    )
    def count_post(
        index: str,
        request: CountRequest,
    ):

        check_index(index)

        return run_count(
            service(),
            request.query,
        )

    # --------------------------------------------
    # mapping
    # --------------------------------------------

    @app.get(
        "/{index}/_mapping"
    )
    def mapping(
        index: str,
    ):

        check_index(index)

        return service().mapping()

    return app


def run_search(
    service: SearchService,
    request: SearchRequest,
):

    try:

        return service.search(
            request
        )

    except UnsupportedQueryError as e:

        raise HTTPException(
            status_code=400,
            detail={
                "type":
                "unsupported_query_exception",
                "reason": str(e),
            },
        )

    except QueryError as e:

        raise HTTPException(
            status_code=400,
            detail={
                "type":
                "query_parsing_exception",
                "reason": str(e),
            },
        )

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail={
                "type":
                "illegal_argument_exception",
                "reason": str(e),
            },
        )


def run_count(
    service: SearchService,
    query: dict | None,
):

    try:

        return service.count(query)

    except QueryError as e:

        raise HTTPException(
            status_code=400,
            detail={
                "type":
                "query_parsing_exception",
                "reason": str(e),
            },
        )

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail={
                "type":
                "illegal_argument_exception",
                "reason": str(e),
            },
        )
