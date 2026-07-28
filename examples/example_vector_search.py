"""ベクトル検索の使用例"""
from nlp4j_local_search import SearchEngine

print("=== テキスト検索の例（既存機能） ===")
with SearchEngine("ja") as engine:
    engine.add("1", "東京都は日本の都道府県のひとつです")
    engine.add("2", "京都は日本の都市です。")
    engine.add("3", "京都市には任天堂の本社があります")
    engine.add_json({"id": "4", "body": "京都府は広いです"})
    
    engine.commit()
    
    print("クエリ: '京都'")
    for r in engine.search("京都", limit=10):
        print(f"  {r.id}: {r.body} (score: {r.score})")

print("\n=== ベクトル検索の例（新機能） ===")
# 2次元ベクトル空間でのベクトル検索
with SearchEngine("ja", vector_dimension=2) as engine:
    # 方角を表すベクトルを追加
    engine.add("1_East", [1.0, 0.0])    # 東
    engine.add("2_North", [1.0, 1.0])   # 北東
    engine.add("3_West", [-1.0, 0.0])   # 西
    engine.add("4_South", [-1.0, -1.0]) # 南西
    
    engine.commit()
    
    # 東寄りのベクトルで検索
    query_vector = [0.9, 0.1]
    print(f"クエリベクトル: {query_vector}")
    for r in engine.search(query_vector, limit=10):
        print(f"  {r.id}: body={r.body} (score: {r.score})")

print("\n完了！")

# Made with Bob
