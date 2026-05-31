"""ベクトル検索機能のテスト"""
import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nlp4j_local_search import SearchEngine


def test_text_search():
    """既存のテキスト検索機能のテスト（既存機能が壊れていないことを確認）"""
    print("=== テキスト検索のテスト ===")
    
    with SearchEngine("ja") as search:
        search.add("1", "東京都は日本の都道府県のひとつです")
        search.add("2", "京都は日本の都市です。")
        search.add("3", "京都市には任天堂の本社があります")
        search.add_json({
            "id": "4",
            "body": "京都府は広いです"
        })
        search.commit()
        
        results = search.search("京都", 10)
        print(f"検索結果数: {len(results)}")
        for i, result in enumerate(results):
            print(f"result[{i}].id: {result.id}")
            print(f"result[{i}].body: {result.body}")
            print(f"result[{i}].score: {result.score}")
        
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"
        print("✓ テキスト検索テスト成功\n")


def test_vector_search():
    """ベクトル検索機能のテスト"""
    print("=== ベクトル検索のテスト ===")
    
    with SearchEngine("ja", vector_dimension=2) as search:
        # 2次元ベクトルを追加
        search.add("1_East", [1.0, 0.0])
        search.add("2_North", [1.0, 1.0])
        search.add("3_West", [-1.0, 0.0])
        search.add("4_South", [-1.0, -1.0])
        search.commit()
        
        # ベクトルで検索
        results = search.search([0.9, 0.1], 10)
        print(f"検索結果数: {len(results)}")
        for i, result in enumerate(results):
            print(f"result[{i}].id: {result.id}")
            print(f"result[{i}].body: {result.body}")
            print(f"result[{i}].score: {result.score}")
            print("---")
        
        assert len(results) == 4, f"Expected 4 results, got {len(results)}"
        # 最も近いのは1_East（東）であるべき
        assert results[0].id == "1_East", f"Expected first result to be '1_East', got '{results[0].id}'"
        print("✓ ベクトル検索テスト成功\n")


def test_vector_dimension_validation():
    """ベクトル次元数のバリデーションテスト"""
    print("=== ベクトル次元数バリデーションのテスト ===")
    
    with SearchEngine("ja", vector_dimension=2) as search:
        try:
            # 次元数が合わないベクトルを追加しようとする
            search.add("test", [1.0, 2.0, 3.0])
            assert False, "Should have raised InvalidDocumentError"
        except Exception as e:
            print(f"期待通りのエラー: {e}")
            assert "dimension mismatch" in str(e).lower()
        
        try:
            # 次元数が合わないベクトルで検索しようとする
            search.add("test", [1.0, 2.0])
            search.commit()
            search.search([1.0, 2.0, 3.0], 10)
            assert False, "Should have raised InvalidDocumentError"
        except Exception as e:
            print(f"期待通りのエラー: {e}")
            assert "dimension mismatch" in str(e).lower()
        
        print("✓ バリデーションテスト成功\n")


def test_mixed_usage_prevention():
    """テキスト検索とベクトル検索の混在防止テスト"""
    print("=== 混在防止のテスト ===")
    
    # vector_dimensionなしでベクトルを追加しようとする
    with SearchEngine("ja") as search:
        try:
            search.add("test", [1.0, 2.0])
            assert False, "Should have raised InvalidDocumentError"
        except Exception as e:
            print(f"期待通りのエラー（ベクトル追加）: {e}")
            assert "vector_dimension must be specified" in str(e).lower()
    
    # vector_dimensionなしでベクトル検索しようとする
    with SearchEngine("ja") as search:
        search.add("test", "テストテキスト")
        search.commit()
        try:
            search.search([1.0, 2.0], 10)
            assert False, "Should have raised InvalidDocumentError"
        except Exception as e:
            print(f"期待通りのエラー（ベクトル検索）: {e}")
            assert "vector_dimension must be specified" in str(e).lower()
    
    print("✓ 混在防止テスト成功\n")


if __name__ == "__main__":
    try:
        test_text_search()
        test_vector_search()
        test_vector_dimension_validation()
        test_mixed_usage_prevention()
        print("=" * 50)
        print("すべてのテストが成功しました！")
        print("=" * 50)
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Made with Bob
