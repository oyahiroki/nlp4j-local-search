# example_vector_search.py の実行準備

## 必要な環境

1. **Python 3.8以上**
2. **Java Runtime Environment (JRE)**
   - JPype1がJavaを呼び出すために必要
   - Java 8以上を推奨

## セットアップ手順

### 1. Javaのインストール確認

コマンドプロンプトまたはPowerShellで以下を実行:

```powershell
java -version
```

Javaがインストールされていない場合は、以下からダウンロード:
- https://www.oracle.com/java/technologies/downloads/
- または OpenJDK: https://adoptium.net/

### 2. パッケージのインストール

プロジェクトのルートディレクトリ（c:/Users/oyahi/git/nlp4j-local-search）で以下を実行:

#### 方法A: 開発モードでインストール（推奨）

```powershell
pip install -e .
```

この方法では、コードの変更が即座に反映されます。

#### 方法B: 通常のインストール

```powershell
pip install .
```

### 3. 依存パッケージの確認

インストールが成功すると、以下のパッケージがインストールされます:
- `jpype1>=1.4.0` (Javaとの連携用)

確認方法:
```powershell
pip list | Select-String jpype1
```

## 実行方法

### example_vector_search.py の実行

```powershell
python example\example_vector_search.py
```

### 期待される出力

```
=== テキスト検索の例（既存機能） ===
クエリ: '京都'
  2: 京都は日本の都市です。 (score: 0.xxxx)
  4: 京都府は広いです (score: 0.xxxx)
  3: 京都市には任天堂の本社があります (score: 0.xxxx)

=== ベクトル検索の例（新機能） ===
クエリベクトル: [0.9, 0.1]
  1_East: body= (score: 0.xxxx)
  2_North: body= (score: 0.xxxx)
  3_West: body= (score: 0.xxxx)
  4_South: body= (score: 0.xxxx)

完了！
```

## トラブルシューティング

### エラー: "No module named 'nlp4j_local_search'"

**原因**: パッケージがインストールされていない

**解決方法**:
```powershell
pip install -e .
```

### エラー: "JVMNotFoundException" または Java関連のエラー

**原因**: Javaがインストールされていない、またはパスが通っていない

**解決方法**:
1. Javaをインストール
2. 環境変数 `JAVA_HOME` を設定
3. `PATH` に `%JAVA_HOME%\bin` を追加

### エラー: "python: コマンドが見つかりません"

**原因**: Pythonがパスに含まれていない

**解決方法**:
- `py` コマンドを試す: `py example\example_vector_search.py`
- または、Pythonのフルパスを指定

## その他のサンプル実行

### 既存のテキスト検索サンプル

```powershell
python example\example.py
```

### テストコードの実行

```powershell
python tests\test_vector_search.py
```

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

## 注意事項

- 初回実行時、JVMの起動に数秒かかる場合があります
- オンメモリ検索のため、プログラム終了後はデータは保持されません
- Windows環境では、PowerShellまたはコマンドプロンプトを使用してください