
# Apache Lucene を利用したオンメモリ検索エンジン

[English](README.md) | 日本語

Elasticsearch、OpenSearch、Apache Solr の基盤技術である Apache Lucene を利用しています。

サーバー構築や Docker は不要です。Python からすぐに検索を始められます。

# nlp4j-local-search

Python から簡単に利用できる、オンメモリのローカル検索エンジンです。

内部的には Apache Lucene ベースの検索エンジンを利用し、日本語・英語などの全文検索を手軽に実行できます。

サーバーの構築や Docker の起動は不要です。

## 特徴

* Python から簡単に利用可能
* オンメモリ検索
* 検索インデックスをディスクに保存しない
* Elasticsearch / OpenSearch / Solr 不要
* Docker 不要
* 日本語検索対応
* 英語検索対応
* Google Colab 対応予定
* Apache Lucene ベース
* 小規模データの検索や NLP 実験に最適

## 利用シーン

* 自然言語処理の実験
* Embedding モデルの評価
* RAG のプロトタイピング
* Jupyter Notebook
* Google Colab
* テストコードでの検索処理
* ローカル検索アプリケーション

## インストール

> **注意**: 現在、PyPI への公開準備中です。それまでは GitHub リポジトリから直接インストールしてください。

### GitHub リポジトリからのインストール

以下のいずれかの方法でインストールできます:

**方法1: pip で直接インストール**

```bash
pip install git+https://github.com/oyahiroki/nlp4j-local-search.git
```

**方法2: リポジトリをクローンしてインストール**

```bash
# リポジトリをクローン
git clone https://github.com/oyahiroki/nlp4j-local-search.git
cd nlp4j-local-search

# 開発モードでインストール
pip install -e .
```

### サンプルプログラムの実行

リポジトリに含まれるサンプルプログラムを実行する場合:

```bash
# リポジトリをクローン（まだの場合）
git clone https://github.com/oyahiroki/nlp4j-local-search.git
cd nlp4j-local-search

# 依存パッケージをインストール
pip install -e .

# サンプルプログラムを実行
python example/example.py
```

実行結果の例:

```
2 京都は日本の都市です。 0.18059490621089935
4 京都府は広いです 0.18059490621089935
3 京都市には任天堂の本社があります 0.16212496161460876
```

## クイックスタート

```python
from nlp4j_local_search import SearchEngine

engine = SearchEngine("ja")

engine.add("1", "東京都は日本の都道府県のひとつです")
engine.add("2", "京都は日本の都市です")
engine.add("3", "京都市には任天堂の本社があります")

engine.commit()

results = engine.search("京都")

for r in results:
    print(r.id, r.body, r.score)
```

## JSON ドキュメントの登録

```python
engine.add_json("""
{
  "id": "1",
  "body": "京都府は広いです"
}
""")
```

## 検索

```python
results = engine.search("京都")
```

件数を指定する場合

```python
results = engine.search("京都", limit=10)
```

## 言語設定

日本語

```python
engine = SearchEngine("ja")
```

英語

```python
engine = SearchEngine("en")
```

## Google Colab での利用

Google Colab でも簡単に利用できます。

### インストール

Colab のセルで以下を実行:

```python
# GitHub リポジトリから直接インストール
!pip install git+https://github.com/oyahiroki/nlp4j-local-search.git
```

### 使用例（一括実行）

```python
from nlp4j_local_search import SearchEngine

# 検索エンジンを初期化
with SearchEngine("ja") as engine:
    # ドキュメントを追加
    engine.add("1", "東京都は日本の都道府県のひとつです")
    engine.add("2", "京都は日本の都市です")
    engine.add("3", "京都市には任天堂の本社があります")
    engine.add_json({"id": "4", "body": "京都府は広いです"})
    
    # インデックスをコミット
    engine.commit()
    
    # 検索を実行
    results = engine.search("京都", limit=10)
    
    # 結果を表示
    for r in results:
        print(f"ID: {r.id}, Score: {r.score:.4f}")
        print(f"Body: {r.body}")
        print("-" * 50)
```

### インタラクティブな使用例（セル単位で実行）

Google Colab では、各セルを個別に実行してインタラクティブに操作できます。

**セル 1: ライブラリのインポートと初期化**

```python
from nlp4j_local_search import SearchEngine

# 検索エンジンを初期化（日本語モード）
engine = SearchEngine("ja")
```

**セル 2: ドキュメントの追加**

```python
# ドキュメントを1件ずつ追加
engine.add("1", "東京都は日本の都道府県のひとつです")
engine.add("2", "京都は日本の都市です")
engine.add("3", "京都市には任天堂の本社があります")
```

**セル 3: JSON形式でドキュメントを追加**

```python
# JSON形式でも追加可能
engine.add_json({"id": "4", "body": "京都府は広いです"})
engine.add_json({"id": "5", "body": "大阪は関西の大都市です"})
```

**セル 4: インデックスのコミット**

```python
# 追加したドキュメントをインデックスに反映
engine.commit()
print("インデックスのコミットが完了しました")
```

**セル 5: 検索の実行**

```python
# 「京都」で検索
results = engine.search("京都", limit=10)

# 結果を表示
for r in results:
    print(f"ID: {r.id}, Score: {r.score:.4f}")
    print(f"Body: {r.body}")
    print("-" * 50)
```

**セル 6: 別のキーワードで検索**

```python
# 「日本」で検索
results = engine.search("日本", limit=5)

for r in results:
    print(f"ID: {r.id}, Score: {r.score:.4f}")
    print(f"Body: {r.body}")
    print("-" * 50)
```

**セル 7: さらにドキュメントを追加して再検索**

```python
# 新しいドキュメントを追加
engine.add("6", "奈良には東大寺があります")
engine.add("7", "神戸は港町として有名です")
engine.commit()

# 再度検索
results = engine.search("関西", limit=10)
for r in results:
    print(f"ID: {r.id}, Score: {r.score:.4f}")
    print(f"Body: {r.body}")
    print("-" * 50)
```

**セル 8: リソースのクリーンアップ**

```python
# 使用後はクローズ
engine.close()
print("検索エンジンをクローズしました")
```

### 注意事項

- Google Colab には Java がプリインストールされているため、追加のセットアップは不要です
- 初回実行時に JVM の起動に数秒かかる場合があります
- セッションをリセットすると、インデックスデータは失われます（オンメモリのため）

## 設計思想

### ローカル検索

本ライブラリはサーバー型検索エンジンではありません。

以下のような環境構築は不要です。

* Elasticsearch
* OpenSearch
* Solr

検索エンジンをローカルプロセス内で直接利用できます。

### オンメモリ

デフォルトでは検索インデックスをメモリ上に構築します。

検索インデックスをディスクへ永続化しません。

そのため、

* 一時的な実験
* テストコード
* Notebook
* 機密データを扱う PoC

などに適しています。

### Python ファースト

内部実装は Java を利用していますが、利用者は Java を意識する必要はありません。

```python
engine = SearchEngine("ja")
```

だけで利用できます。

## ロードマップ

* [x] オンメモリ検索
* [x] 日本語検索
* [x] JSON ドキュメント登録
* [x] Python パッケージ公開
* [ ] Google Colab 対応
* [ ] ベクトル検索
* [ ] Aggregation
* [ ] JSON Query DSL
* [ ] OpenSearch 互換 API

## ライセンス

Apache License 2.0

## 作者

Hiroki Oya

GitHub:
https://github.com/oyahiroki


