# ベクトル検索機能の実装

## 概要

LocalSearchTestCase.javaの`testSearch100()`を参考に、Pythonコードにベクトル検索機能を追加しました。

## 実装内容

### 1. SearchEngineクラスの拡張 (src/nlp4j_local_search/engine.py)

#### コンストラクタの変更
- `vector_dimension` パラメータを追加
- ベクトル次元数を指定すると、Java側の `LocalSearch(lang, vectorDimension)` コンストラクタを呼び出す

```python
engine = SearchEngine("ja", vector_dimension=2)
```

#### addメソッドの拡張
- `body` パラメータが `list` または `tuple` の場合、ベクトルとして扱う
- ベクトル次元数のバリデーションを実装
- 既存のテキスト追加機能は維持

```python
# テキスト追加（既存機能）
engine.add("1", "テキスト")

# ベクトル追加（新機能）
engine.add("1", [1.0, 0.0])
```

#### searchメソッドの拡張
- `query` パラメータが `list` または `tuple` の場合、ベクトル検索を実行
- ベクトル次元数のバリデーションを実装
- 既存のテキスト検索機能は維持

```python
# テキスト検索（既存機能）
results = engine.search("京都")

# ベクトル検索（新機能）
results = engine.search([0.9, 0.1])
```

### 2. サンプルコードの追加

#### example/example_vector_search.py
- テキスト検索とベクトル検索の両方の使用例を含む
- 2次元ベクトル空間での方角検索の例を実装

### 3. テストコードの追加

#### tests/test_vector_search.py
- テキスト検索のテスト（既存機能の動作確認）
- ベクトル検索のテスト
- ベクトル次元数のバリデーションテスト
- テキスト検索とベクトル検索の混在防止テスト

### 4. ドキュメントの更新

#### README_ja.md
- ベクトル検索の使い方を追加
- Embeddingベクトルの検索例を追加
- ロードマップを更新（ベクトル検索を完了済みに変更）

## 既存機能への影響

### 後方互換性の維持
- `vector_dimension` パラメータはオプショナル（デフォルト: `None`）
- 既存のコードは変更なしで動作する
- テキスト検索機能は完全に維持

### 動作の分離
- `vector_dimension` を指定した場合はベクトル検索モード
- 指定しない場合は従来のテキスト検索モード
- 両モードの混在を防ぐバリデーションを実装

## 使用例

### テキスト検索（既存機能）
```python
from nlp4j_local_search import SearchEngine

with SearchEngine("ja") as engine:
    engine.add("1", "東京都は日本の都道府県のひとつです")
    engine.add("2", "京都は日本の都市です。")
    engine.commit()
    
    results = engine.search("京都", limit=10)
    for r in results:
        print(r.id, r.body, r.score)
```

### ベクトル検索（新機能）
```python
from nlp4j_local_search import SearchEngine

with SearchEngine("ja", vector_dimension=2) as engine:
    engine.add("1_East", [1.0, 0.0])
    engine.add("2_North", [1.0, 1.0])
    engine.add("3_West", [-1.0, 0.0])
    engine.add("4_South", [-1.0, -1.0])
    engine.commit()
    
    results = engine.search([0.9, 0.1], limit=10)
    for r in results:
        print(r.id, r.body, r.score)
```

## テスト方法

```bash
# テストコードの実行
python tests/test_vector_search.py

# サンプルコードの実行
python example/example_vector_search.py
```

## 実装の参考

- LocalSearchTestCase.java の `testSearch100()` メソッド
- Java側の `LocalSearch(String lang, int vectorDimension)` コンストラクタ
- Java側の `add(String id, float[] vector)` メソッド
- Java側の `search(float[] vector, int limit)` メソッド