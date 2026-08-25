# example_010_auto_analyze_en.py
#
# English text automatic morphological analysis (auto_analyze)
#
# SearchEngine("en") defaults to auto_analyze=True.
# Adding natural English sentences with add() causes the Java side to
# automatically analyze the text and populate fields such as:
#   word.noun  (nouns)
#   word.verb  (base-form verbs)
#
# These can then be aggregated with aggregate().
# OpenNLP models bundled inside the JAR are used for English analysis.

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
    # 1. Aggregate all nouns across all documents
    # ------------------------------------------------------------------
    print("=== All documents: word.noun aggregation ===")
    result = engine.aggregate("word.noun", size=50)
    for bucket in result["aggregations"]["word.noun"]["buckets"]:
        print(f"  {bucket['key']:12s}  {bucket['doc_count']} doc(s)")

    # ------------------------------------------------------------------
    # 2. Aggregate all verbs across all documents
    # ------------------------------------------------------------------
    print()
    print("=== All documents: word.verb aggregation ===")
    result = engine.aggregate("word.verb", size=50)
    for bucket in result["aggregations"]["word.verb"]["buckets"]:
        print(f"  {bucket['key']:12s}  {bucket['doc_count']} doc(s)")

    # ------------------------------------------------------------------
    # 3. Full-text search combined with noun aggregation
    # ------------------------------------------------------------------
    print()
    print('=== Documents containing "park": word.noun aggregation ===')
    result = engine.aggregate("word.noun", size=50, query="park")
    for bucket in result["aggregations"]["word.noun"]["buckets"]:
        print(f"  {bucket['key']:12s}  {bucket['doc_count']} doc(s)")

    # ------------------------------------------------------------------
    # 4. Full-text search: documents about "cat"
    # ------------------------------------------------------------------
    print()
    print('=== Full-text search: "cat" ===')
    for r in engine.search("cat", 10):
        print(f"  [{r.id}] {r.body}  (score={r.score:.4f})")

# Expected output (excerpt):
# === All documents: word.noun aggregation ===
#   cat           4 doc(s)
#   dog           4 doc(s)
#   park          4 doc(s)
#   mouse         3 doc(s)
#   mat           1 doc(s)
#   children      1 doc(s)
#   tree          1 doc(s)
#   kitchen       1 doc(s)
#   table         1 doc(s)
#   flower        1 doc(s)
# === All documents: word.verb aggregation ===
#   play          1 doc(s)
#   see           1 doc(s)
#   hide          1 doc(s)
#   bark          1 doc(s)
#   run           1 doc(s)
#   chase         1 doc(s)
#   walk          1 doc(s)
#   sit           1 doc(s)
