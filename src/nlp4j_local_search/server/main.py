import argparse

import uvicorn

from .app import create_app
from .service import ServerConfig


def main():

    parser = argparse.ArgumentParser(
        prog=(
            "nlp4j-local-search-server"
        )
    )

    parser.add_argument(
        "--lang",
        choices=[
            "ja",
            "en",
        ],
        required=True,
    )

    parser.add_argument(
        "--index",
        default="default",
    )

    parser.add_argument(
        "--data",
        default=None,
    )

    parser.add_argument(
        "--auto-analyze",
        action="store_true",
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=9200,
    )

    args = parser.parse_args()

    config = ServerConfig(
        lang=args.lang,
        index_name=args.index,
        auto_analyze=(
            args.auto_analyze
        ),
        data_path=args.data,
    )

    app = create_app(
        config
    )

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        workers=1,
    )


if __name__ == "__main__":
    main()
