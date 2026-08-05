# セットアップと実行ガイド

## 必要な環境

- **Python 3.8 以上**
- **Java Runtime Environment (JRE 8 以上)**
  - JPype1 が Java を呼び出すために必要
- **jpype1** （pip で自動インストールされます）

---

## セットアップ手順

### 1. Java のインストール確認

```powershell
java -version
```

Java がインストールされていない場合は以下からダウンロードしてください。

- Oracle JDK: https://www.oracle.com/java/technologies/downloads/
- OpenJDK: https://adoptium.net/

### 2. パッケージのインストール

リポジトリのルートディレクトリで以下を実行します。

#### 方法A: 開発モードでインストール（推奨）

```powershell
pip install -e .
```

コードの変更が即座に反映されます。

#### 方法B: PyPI からインストール

```powershell
pip install nlp4j-local-search
```

### 3. 依存パッケージの確認

```powershell
pip list | Select-String jpype1
```

---

## サンプルの実行

### example_001: キーワード検索

```powershell
python examples\example_001_keywordsearch.py
```

期待される出力:

```
2 京都は日本の都市です。 0.18059490621089935
4 京都府は広いです 0.18059490621089935
3 京都市には任天堂の本社があります 0.16212496161460876
```

### example_002: ベクトル検索

```powershell
python examples\example_002_vector_search.py
```

期待される出力:

```
=== テキスト検索の例（既存機能） ===
クエリ: '京都'
  2: 京都は日本の都市です。 (score: 0.xxxx)
  4: 京都府は広いです (score: 0.xxxx)
  3: 京都市には任天堂の本社があります (score: 0.xxxx)

=== ベクトル検索の例（新機能） ===
クエリベクトル: [0.9, 0.1]
  1_East: body=None (score: 0.xxxx)
  2_North: body=None (score: 0.xxxx)
  4_South: body=None (score: 0.xxxx)
  3_West: body=None (score: 0.xxxx)

完了！
```

### example_003: フィールド検索

フィールド値（`category`、`country` など）による完全一致絞り込みのサンプルです。

```powershell
python examples\example_003_field_search.py
```

期待される出力:

```
=== Field search: category="city" ===
  [1] Kyoto is a historic city in Japan.
  [3] Tokyo is the capital city of Japan.
  [4] Paris is the capital city of France.
=== Field search: category="company" ===
  [2] Nintendo is headquartered in Kyoto, Japan.
  [5] Sony is a Japanese multinational company.
...
```

### example_004: キーワード検索 ＋ フィールド絞り込み

全文検索とフィールド絞り込みを同時に行うサンプルです。

```powershell
python examples\example_004_keyword_and_field_search.py
```

期待される出力:

```
=== Keyword + field: "Kyoto" + category="company" ===
  [2] score=0.xxxx  Nintendo is headquartered in Kyoto, Japan.
=== Keyword + field: "Japan" + category="city" ===
  [1] score=0.xxxx  Kyoto is a historic city in Japan.
  [3] score=0.xxxx  Tokyo is the capital city of Japan.
...
```

### example_005: ベクトル検索 ＋ フィールド絞り込み

ベクトル登録時に `fields` を付け、検索時に `filters` で絞り込むサンプルです。
フィルターは KNN クエリの内部で適用されるため、絞り込み後の文書集合から正しく上位 k 件が取得されます。

```powershell
python examples\example_005_vector_and_field_search.py
```

期待される出力:

```
=== Vector search (no filter): queryVector=[0.9, 0.1] ===
  [3_travel_East]  score=0.xxxx
  [1_tech_East]    score=0.xxxx
  ...
=== Vector + field: queryVector=[0.9, 0.1] + category="tech" ===
  [1_tech_East]    score=0.xxxx
  [5_tech_NE]      score=0.xxxx
  [2_tech_North]   score=0.xxxx
...
```

---

## テストの実行

### すべてのテストを実行

```powershell
python -m pytest tests\ -v
```

### 個別に実行

```powershell
# 日本語テキスト検索 + ベクトル検索
python tests\test_vector_search.py

# 英語テキスト検索
python tests\test_search_en.py

# フィールド絞り込み（新機能）
python tests\test_field_search.py
```

---

## 開発環境での確認

### インストール状態の確認

```powershell
pip show nlp4j-local-search
```

### パッケージの再インストール

```powershell
pip uninstall nlp4j-local-search
pip install -e .
```

---

## トラブルシューティング

### エラー: `No module named 'nlp4j_local_search'`

**原因**: パッケージがインストールされていない

**解決方法**:

```powershell
pip install -e .
```

### エラー: `JVMNotFoundException` または Java 関連のエラー

**原因**: Java がインストールされていない、またはパスが通っていない

**解決方法**:

1. Java をインストール
2. 環境変数 `JAVA_HOME` を設定
3. `PATH` に `%JAVA_HOME%\bin` を追加

設定後、PowerShell を再起動して確認:

```powershell
java -version
```

### エラー: `python: コマンドが見つかりません`

**原因**: Python がパスに含まれていない

**解決方法**:

```powershell
py examples\example_001_keywordsearch.py
```

---

## 注意事項

- 初回実行時、JVM の起動に数秒かかる場合があります
- オンメモリ検索のため、プログラム終了後はデータは保持されません
- Windows 環境では PowerShell またはコマンドプロンプトを使用してください
