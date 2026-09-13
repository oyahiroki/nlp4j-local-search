import time

from nlp4j_local_search import SearchEngine
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA = BASE_DIR / "jawiki-20260801-pages-articles_compact_manga.jsonl"

def print_results(results):
    for r in results:
        print(f"[{r.id}] score={r.score:.4f}")
        print(r.body)
        print()


with SearchEngine("ja") as engine:

    # ------------------------------------------------------------
    # 1. Load about 30,000 manga-related Wikipedia documents
    # ------------------------------------------------------------
    print("=== Load ===")
    start = time.perf_counter()
    engine.data(str(DATA)).load()
    elapsed = time.perf_counter() - start
    count = engine.count()
    rate = count / elapsed
    
    print(
        f"Loaded {count:,} documents in {elapsed:.2f} seconds "
        f"({rate:,.0f} docs/sec)."
    )
    print()

    # ------------------------------------------------------------
    # 2. Inspect the index
    # ------------------------------------------------------------
    print("=== Fields ===")

    print(engine.fields())
    print()


    print("=== Aggregatable fields ===")

    print(engine.aggregatable_fields())
    print()


    # ------------------------------------------------------------
    # 3. Simple full-text search
    # ------------------------------------------------------------
    print("=== Search: 高橋留美子 ===")

    results = engine.search("高橋留美子", limit=5)
    print_results(results)


    # ------------------------------------------------------------
    # 4. Phrase search
    # ------------------------------------------------------------
    print('=== Search: "週刊少年サンデー" ===')

    results = engine.search(
        'text_ja:"週刊少年サンデー"',
        limit=5,
    )
    print_results(results)


    # ------------------------------------------------------------
    # 5. Search by category
    # ------------------------------------------------------------
    print("=== Category: 恋愛漫画 ===")

    results = engine.search(
        "category_s:恋愛漫画",
        limit=10,
    )
    print_results(results)


    # ------------------------------------------------------------
    # 6. Combine full-text and structured fields
    # ------------------------------------------------------------
    print("=== 高橋留美子 AND 恋愛漫画 ===")

    results = engine.search(
        "text_ja:高橋留美子 AND category_s:恋愛漫画",
        limit=10,
    )
    print_results(results)


    # ------------------------------------------------------------
    # 7. Date range search
    # ------------------------------------------------------------
    print("=== Updated since 2026 ===")

    results = engine.search(
        "timestamp_dt:[2026-01-01 TO *]",
        limit=10,
    )
    print_results(results)


    # ------------------------------------------------------------
    # 8. Explore popular categories
    # ------------------------------------------------------------
    print("=== Popular categories ===")

    print(
        engine.view(
            "category_s",
            size=20,
        )
    )


    # ------------------------------------------------------------
    # 9. What categories characterize documents about 高橋留美子?
    # ------------------------------------------------------------
    print("=== Characteristic categories: 高橋留美子 ===")

    print(
        engine.view(
            "category_s",
            "text_ja:高橋留美子",
            size=100,
        ).filter(min_count=3)
    )