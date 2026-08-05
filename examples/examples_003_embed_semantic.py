# examples_003_embed_semantic.py

# !pip install -q nlp4j-local-search-embedding==0.1.0
# !java -version

from nlp4j_local_search_embedding import SemanticSearch

app = SemanticSearch("ja")

app.add({
    "doc1": "自動車が走っています。",
    "doc2": "自転車を買います",
    "doc3": "サイクリングが趣味です",
    "doc4": "Go shopping by bicycle."
})

app.commit()

results = app.search("自転車", limit=10)

print("=== Search results ===")
print(f"number of results: {len(results)}")

for i, result in enumerate(results):
    print(f"result[{i}].id: {result.id}")
    print(f"result[{i}].text: {result.text}")
    print(f"result[{i}].score: {result.score}")
    print(f"result[{i}].metadata: {result.metadata}")
    print("---")

# expected result


# === Search results ===
# number of results: 4
# result[0].id: doc2
# result[0].text: 自転車を買います
# result[0].score: 0.9391793012619019
# result[0].metadata: {}
# ---
# result[1].id: doc3
# result[1].text: サイクリングが趣味です
# result[1].score: 0.9307862520217896
# result[1].metadata: {}
# ---
# result[2].id: doc4
# result[2].text: Go shopping by bicycle.
# result[2].score: 0.9053230285644531
# result[2].metadata: {}
# ---
# result[3].id: doc1
# result[3].text: 自動車が走っています。
# result[3].score: 0.8970762491226196
# result[3].metadata: {}
# ---
