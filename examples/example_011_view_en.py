# example_011_view_en.py
#
# English text mining with relative_rate() — relativeRate analysis
#
# relative_rate() returns the characteristic terms for a specific subset of
# documents defined by (query_field, query_value).
#
#   relative_rate = (term rate in target docs) / (term rate in all docs)
#
# A relative_rate > 1.0 means the term appears more often in the target
# subset than in the whole corpus.
# All calculation is done on the Java side (LocalAnalytics); Python only
# receives the result as an AnalyticsResult object.

from nlp4j_local_search import SearchEngine

DOCUMENTS = [
    ("1",  "The cat sat on the mat"),
    ("2",  "The cat chased the mouse"),
    ("3",  "The dog ran across the park"),
    ("4",  "The dog barked at the cat"),
    ("5",  "A mouse hid under the table"),
    ("6",  "The park has many trees and flowers"),
    ("7",  "Children played in the park"),
    ("8",  "The dog and the cat are friends"),
    ("9",  "She saw a mouse in the kitchen"),
    ("10", "He walked his dog in the park"),
]

with SearchEngine("en") as engine:

    for doc_id, body in DOCUMENTS:
        engine.add(doc_id, body)

    engine.commit()

    # ------------------------------------------------------------------
    # 1. Nouns characteristic of documents that mention "cat"
    # ------------------------------------------------------------------
    print("=== Characteristic word.noun for documents about 'cat' ===")
    result = engine.relative_rate(
        query_field="word.noun",
        query_value="cat",
        field="word.noun",
        size=100,
    )
    print(f"  Target doc count: {result.count}  Total doc count: {result.total_count}")
    for bucket in result.buckets:
        print(
            f"  {bucket.key:12s}"
            f"  count={bucket.count}"
            f"  all_count={bucket.all_count}"
            f"  relative_rate={bucket.relative_rate:.4f}"
        )

    # ------------------------------------------------------------------
    # 2. Verbs characteristic of documents that mention "dog"
    # ------------------------------------------------------------------
    print()
    print("=== Characteristic word.verb for documents about 'dog' ===")
    result = engine.relative_rate(
        query_field="word.noun",
        query_value="dog",
        field="word.verb",
        size=100,
    )
    for bucket in result.buckets:
        print(
            f"  {bucket.key:12s}"
            f"  count={bucket.count}"
            f"  all_count={bucket.all_count}"
            f"  relative_rate={bucket.relative_rate:.4f}"
        )

    # ------------------------------------------------------------------
    # 3. Nouns characteristic of documents that mention "park"
    # ------------------------------------------------------------------
    print()
    print("=== Characteristic word.noun for documents about 'park' ===")
    result = engine.relative_rate(
        query_field="word.noun",
        query_value="park",
        field="word.noun",
        size=100,
    )
    for bucket in result.buckets:
        print(
            f"  {bucket.key:12s}"
            f"  count={bucket.count}"
            f"  all_count={bucket.all_count}"
            f"  relative_rate={bucket.relative_rate:.4f}"
        )

# Expected output:
# === Characteristic word.noun for documents about 'cat' ===
#   Target doc count: 4  Total doc count: 10
#   cat           count=4  all_count=4  relative_rate=2.5000
#   mat           count=1  all_count=1  relative_rate=2.5000
#   dog           count=2  all_count=4  relative_rate=1.2500
#   mouse         count=1  all_count=3  relative_rate=0.8333
# === Characteristic word.verb for documents about 'dog' ===
#   bark          count=1  all_count=1  relative_rate=2.5000
#   friend        count=1  all_count=1  relative_rate=2.5000
#   run           count=1  all_count=1  relative_rate=2.5000
#   walk          count=1  all_count=1  relative_rate=2.5000
# === Characteristic word.noun for documents about 'park' ===
#   park          count=4  all_count=4  relative_rate=2.5000
#   children      count=1  all_count=1  relative_rate=2.5000
#   tree          count=1  all_count=1  relative_rate=2.5000
#   flower        count=1  all_count=1  relative_rate=2.5000
#   dog           count=2  all_count=4  relative_rate=1.2500
