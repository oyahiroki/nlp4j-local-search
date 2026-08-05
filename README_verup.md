# Java モジュール バージョンアップ手順

このドキュメントでは、`nlp4j-local-search` が内部で使用している Java JAR ファイル (`nlp4j-localsearch.jar`) を新しいバージョンに差し替える手順を説明します。

## 背景・構成の概要

このプロジェクトは Python から Java ライブラリを呼び出す構成になっています。

```
Python (nlp4j_local_search)
  └── JPype1 経由で JVM を起動
        └── nlp4j.lucene.LocalSearch (Java クラス)
              └── nlp4j-localsearch.jar (Jar-in-Jar 形式)
                    └── Apache Lucene 等の依存 JAR が同梱
```

- JAR ファイルの配置場所: `src/nlp4j_local_search/jars/nlp4j-localsearch.jar`
- JAR の読み込み: [`jvm.py`](src/nlp4j_local_search/jvm.py) の `default_jar_path()` が参照
- Java クラスの利用: [`engine.py`](src/nlp4j_local_search/engine.py) が `nlp4j.lucene.LocalSearch` を呼び出し

---

## 前提条件

- 新しい JAR ファイルが手元にある
- JAR の Java パッケージ名・クラス名 (`nlp4j.lucene.LocalSearch`) が変わっていない
- Python 開発環境がセットアップ済み (`pip install -e .` で動作確認済み)
- Java 8 以上がインストール済み (`java -version` で確認)

---

## 手順

### 1. 旧 JAR のバックアップ

念のため旧バージョンの JAR をバックアップします。

```bash
cp src/nlp4j_local_search/jars/nlp4j-localsearch.jar \
   src/nlp4j_local_search/jars/nlp4j-localsearch.<旧バージョン>.jar
```

例（旧バージョンが 0.1.0 の場合）:

```bash
cp src/nlp4j_local_search/jars/nlp4j-localsearch.jar \
   src/nlp4j_local_search/jars/nlp4j-localsearch.0.1.0.jar
```

### 2. 新しい JAR を配置

新しい JAR ファイルを `nlp4j-localsearch.jar` という名前でコピーします。

```bash
cp /path/to/new/nlp4j-localsearch-<新バージョン>.jar \
   src/nlp4j_local_search/jars/nlp4j-localsearch.jar
```

> **重要**: ファイル名は必ず `nlp4j-localsearch.jar` にしてください。  
> [`jvm.py`](src/nlp4j_local_search/jvm.py) の `default_jar_path()` がこの名前を参照しています。

### 3. JAR の内容確認

新しい JAR が正しく配置されているか、また必要なクラスが含まれているかを確認します。

```bash
# ファイルサイズ確認
ls -lh src/nlp4j_local_search/jars/nlp4j-localsearch.jar

# JAR 内のクラスを確認 (LocalSearch クラスが存在するか)
jar tf src/nlp4j_local_search/jars/nlp4j-localsearch.jar | grep LocalSearch

# 内包する依存 JAR の確認 (Jar-in-Jar 構成の確認)
jar tf src/nlp4j_local_search/jars/nlp4j-localsearch.jar | grep "\.jar$"
```

期待される出力例:

```
nlp4j/lucene/LocalSearch.class
nlp4j/lucene/SearchResult.class
```

### 4. Python パッケージを再インストール

開発環境で JAR を反映させるため、パッケージを再インストールします。

```bash
pip install -e .
```

### 5. 動作確認テスト

Python からテキスト検索が正常に動作するか確認します。

```python
# quick_test.py として保存して実行
import nlp4j_local_search

with nlp4j_local_search.SearchEngine("ja") as engine:
    engine.add("1", "東京都は日本の都道府県のひとつです")
    engine.add("2", "京都は日本の都市です。")
    engine.add("3", "京都市には任天堂の本社があります")
    engine.commit()
    results = engine.search("京都", 10)
    print(f"件数: {len(results)}")
    for r in results:
        print(f"  id={r.id}, score={r.score:.4f}, body={r.body}")
```

```bash
python quick_test.py
```

期待される出力:

```
件数: 2
  id=2, score=0.xxxx, body=京都は日本の都市です。
  id=3, score=0.xxxx, body=京都市には任天堂の本社があります
```

テストスクリプトを使う場合:

```bash
python -m pytest tests/
```

### 6. pyproject.toml のバージョンを更新

JAR の更新に合わせて Python パッケージのバージョンも上げます。

```toml
[project]
name = "nlp4j-local-search"
version = "0.3.0"   # ← 新しいバージョンに変更
```

バージョニングの方針（例）:

| 変更内容 | バージョンの上げ方 |
|---|---|
| JAR のバグ修正のみ | `0.2.0` → `0.2.1` (patch) |
| JAR に機能追加 | `0.2.0` → `0.3.0` (minor) |
| JAR の API に破壊的変更 | `0.2.0` → `1.0.0` (major) |

### 7. Python パッケージのビルドと確認

```bash
# 旧ビルド成果物の削除
rm -rf dist build *.egg-info src/*.egg-info

# ビルド
python -m build

# JAR が wheel に含まれているか確認
unzip -l dist/*.whl | grep jar
```

期待される出力例:

```
nlp4j_local_search/jars/nlp4j-localsearch.jar
```

### 8. Git コミット

```bash
git add src/nlp4j_local_search/jars/nlp4j-localsearch.jar pyproject.toml
git commit -m "Update Java JAR to v<新バージョン>"
git tag v<新バージョン>
git push origin main
git push origin v<新バージョン>
```

---

## Java クラスの API が変わった場合の追加作業

JAR のバージョンアップで `nlp4j.lucene.LocalSearch` の API（メソッドシグネチャなど）が変わった場合は、Python 側のコードも修正が必要です。

| 修正対象ファイル | 内容 |
|---|---|
| [`engine.py`](src/nlp4j_local_search/engine.py) | `LocalSearch` の呼び出し部分 (`add`, `search`, `commit`, `close`) |
| [`result.py`](src/nlp4j_local_search/result.py) | `SearchResult` の Java オブジェクトからの変換処理 |
| [`jvm.py`](src/nlp4j_local_search/jvm.py) | JAR 読み込みパスやネスト JAR の展開処理 |

変更後は必ず手順 5 の動作確認を実施してください。

---

## トラブルシューティング

### JVMStartError: Failed to extract nested JARs

JAR が壊れているか、Jar-in-Jar 形式でない可能性があります。

```bash
# ZIP として開けるか確認
python -c "import zipfile; print(zipfile.is_zipfile('src/nlp4j_local_search/jars/nlp4j-localsearch.jar'))"
```

`True` が返れば正常な JAR です。

### JavaSearchError: Failed to import Java class

`nlp4j.lucene.LocalSearch` クラスが JAR に存在しない場合に発生します。手順 3 で `LocalSearch.class` が含まれているか再確認してください。

### 旧バージョンの JAR に戻す

```bash
cp src/nlp4j_local_search/jars/nlp4j-localsearch.<旧バージョン>.jar \
   src/nlp4j_local_search/jars/nlp4j-localsearch.jar
pip install -e .
```

---

## 関連ドキュメント

- [README_build.md](README_build.md) — PyPI へのリリース手順
- [SETUP_AND_RUN.md](SETUP_AND_RUN.md) — 開発環境のセットアップと実行方法
