import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nlp4j_local_search import SearchEngine


def test_text_search():
    print("=== Search test ===")
    
    with SearchEngine("en") as search:
        search.add("1", "I run every morning")
        search.add("2", "She runs every day")
        search.add("3", "He is running in the park")
        search.add("4", "This document is about search engines")
        search.commit()
        
        results = search.search("text_en:run", 10)
        print(f"number of results: {len(results)}")
        for i, result in enumerate(results):
            print(f"result[{i}].id: {result.id}")
            print(f"result[{i}].body: {result.body}")
            print(f"result[{i}].score: {result.score}")
        
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"
        print("✓ OK\n")


if __name__ == "__main__":
    try:
        test_text_search()
        print("=" * 50)
        print("OK!")
        print("=" * 50)
    except Exception as e:
        print(f"\n❌ NG: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

