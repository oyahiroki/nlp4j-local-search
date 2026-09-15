import gzip
import json
import traceback

from nlp4j_local_search import SearchEngine


PATH = (
    "examples_demo/"
    "jawiki-20260801-pages-articles_compact_manga.jsonl.gz"
)


with SearchEngine(
    "ja",
    auto_analyze=True,
) as engine:

    with gzip.open(
        PATH,
        "rt",
        encoding="utf-8",
    ) as f:

        count = 0

        for line_no, line in enumerate(f, start=1):

            line = line.strip()

            if not line:
                continue

            doc = json.loads(line)
            count += 1

            try:
                engine.add_json(doc)

            except Exception as e:

                print()
                print("=== FAILED DOCUMENT ===")
                print(f"line      : {line_no}")
                print(f"document  : {count}")
                print(f"id        : {doc.get('id')}")
                print(f"title_s   : {doc.get('title_s')}")

                text = doc.get("text_ja")

                print(f"text type : {type(text).__name__}")
                print(f"text      : {repr(text)[:1000]}")

                print()
                print("fields:")
                for key, value in doc.items():
                    print(
                        f"  {key}: "
                        f"{type(value).__name__} "
                        f"{repr(value)[:300]}"
                    )

                print()
                traceback.print_exc()

                raise

            if count % 100 == 0:
                print(f"Processed: {count:,}")

    engine.commit()

    print()
    print(f"OK: {engine.count():,} documents")
