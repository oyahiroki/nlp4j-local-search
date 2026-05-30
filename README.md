
# Apache Lucene を利用したオンメモリ検索エンジン

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

PyPI からのインストール:

```bash
pip install nlp4j-local-search
```

### 開発版のインストール

GitHub リポジトリから最新の開発版をインストールする場合:

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


