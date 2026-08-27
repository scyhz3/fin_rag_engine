# fin-rag-engine

日本の EDINET 開示書類を対象とした RAG データ処理プロジェクトです。元データの保存から書類識別、本文抽出、チャンク作成、Embedding の生成、ベクトル検索までを実装しています。

## 現在の機能

- EDINET API を呼び出し、日付ごとの提出書類メタデータを取得します。
- 設定した企業の有価証券報告書と訂正有価証券報告書だけを抽出します。
- 完全な `metadata.json`、XBRL ZIP、および提供されている場合は PDF を保存します。
- 各提出書類を `EDINET code/doc_id` 単位で分けて保存します。
- 保存済みのメタデータと XBRL ZIP から書類情報を識別します。
- 原本と訂正報告書をまとめ、各報告書の最新バージョンだけを選択します。
- Inline XBRL の本文ファイルから、順序と出典を保持したテキストを抽出します。
- HTML の見出し階層を使い、本文を出典付きの章単位に構造化します。
- 章の境界を保ちながら、本文を検索用の小さなチャンクに分割します。
- チャンクをバッチ単位で Embedding モデルへ渡し、ベクトル付きデータへ変換します。
- ローカルの Ruri v3 を使い、日本語文書と検索クエリのベクトルを生成します。
- OpenAI Embeddings API も任意の代替バックエンドとして保持します。
- Qdrant Local にチャンクとベクトルを保存し、検索条件を使って類似文章を取得します。

現在のダウンロード対象となる書類種別は次のとおりです。

- `docTypeCode = "120"`：有価証券報告書
- `docTypeCode = "130"`：訂正有価証券報告書

## プロジェクト構成

```text
fin_rag_engine/
├── download_raw.py
├── pyproject.toml
├── uv.lock
├── README.md
├── src/
│   └── finrag/
│       ├── __init__.py
│       ├── type.py
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── edinet_client.py
│       │   ├── downloader.py
│       │   ├── identifier.py
│       │   ├── section_extractor.py
│       │   └── xbrl_extractor.py
│       ├── processing/
│           ├── __init__.py
│           ├── chunker.py
│           ├── embedding.py
│           ├── openai_embedding_client.py
│           └── ruri_embedding_client.py
│       └── storage/
│           ├── __init__.py
│           ├── qdrant_vector_store.py
│           └── vector_store.py
├── tests/
│   ├── test_chunker.py
│   ├── test_edinet.py
│   ├── test_embedding.py
│   ├── test_identifier.py
│   ├── test_openai_embedding_client.py
│   ├── test_qdrant_vector_store.py
│   ├── test_ruri_embedding_client.py
│   ├── test_section_extractor.py
│   └── test_xbrl_extractor.py
└── data/
    └── raw/
        └── edinet/
```

### ファイルの説明

| ファイル | 役割 |
|---|---|
| `download_raw.py` | 元データをダウンロードするコマンドのエントリーポイントです。日付引数と `EDINET_API` 環境変数を読み込みます。 |
| `pyproject.toml` | Python バージョン、プロジェクト情報、依存関係を定義します。 |
| `uv.lock` | `uv` が生成した依存関係のロックファイルです。 |
| `src/finrag/type.py` | ダウンロード対象企業、対応書類種別、識別に使う DEI 項目を定義します。 |
| `src/finrag/ingestion/edinet_client.py` | EDINET の書類一覧 API と書類取得 API をラップします。 |
| `src/finrag/ingestion/downloader.py` | 対象書類を抽出し、メタデータ、ZIP、PDF を元データ用ディレクトリへ保存します。 |
| `src/finrag/ingestion/identifier.py` | メタデータと XBRL ZIP から書類を識別し、原本と訂正報告書のうち最新バージョンを選択します。 |
| `src/finrag/ingestion/section_extractor.py` | HTML 見出しの階層を保ちながら、XBRL 本文を章単位に構造化します。 |
| `src/finrag/ingestion/xbrl_extractor.py` | Inline XBRL の本文から、元ファイルと順序を保持した可読テキストを抽出します。 |
| `src/finrag/processing/chunker.py` | 章をまたがずに本文を分割し、検索用メタデータを持つチャンクを作成します。 |
| `src/finrag/processing/embedding.py` | Embedding モデルの共通インターフェースを定義し、チャンクをバッチ単位でベクトル化します。 |
| `src/finrag/processing/openai_embedding_client.py` | OpenAI Embeddings API へテキストを送信し、入力順のベクトルを取得します。 |
| `src/finrag/processing/ruri_embedding_client.py` | Ruri v3 をローカルで実行し、用途別の接頭辞を付けて日本語ベクトルを生成します。 |
| `src/finrag/storage/vector_store.py` | ベクトルストアの共通インターフェース、検索条件、検索結果を定義します。 |
| `src/finrag/storage/qdrant_vector_store.py` | Qdrant Local への保存、更新、メタデータ絞り込み、類似度検索を実装します。 |
| `tests/test_chunker.py` | チャンクの長さ、重複部分、メタデータの引継ぎを検証します。 |
| `tests/test_edinet.py` | EDINET ダウンロード機能のテストファイルです。現在、テストはまだ追加されていません。 |
| `tests/test_embedding.py` | バッチ処理、元チャンクの保持、ベクトル次元の検証を行います。 |
| `tests/test_identifier.py` | 書類識別と訂正報告書の選択ルールを検証します。 |
| `tests/test_openai_embedding_client.py` | API リクエスト、レスポンス順序、入力とエラー処理を検証します。 |
| `tests/test_qdrant_vector_store.py` | ベクトルの永続化、更新、絞り込み、モデル一致を検証します。 |
| `tests/test_ruri_embedding_client.py` | 文書とクエリの接頭辞、正規化オプション、空入力の処理を検証します。 |
| `tests/test_section_extractor.py` | 章の階層、本文の所属、順序を検証します。 |
| `tests/test_xbrl_extractor.py` | XBRL 本文の選択、順序、テキスト整形を検証します。 |
| `data/raw/edinet/` | ローカルの元データ用ディレクトリです。ダウンロードした内容は Git にコミットしません。 |

## 元データの構成

EDINET への各提出書類は、個別の `doc_id` ディレクトリに保存されます。

```text
data/raw/edinet/
└── E02655/
    └── S100TUQ8/
        ├── metadata.json
        ├── document.zip
        └── document.pdf
```

- `E02655`：企業の EDINET コードです。
- `S100TUQ8`：当該提出書類の EDINET `doc_id` です。
- `metadata.json`：企業、書類種別、提出日時、会計期間、訂正関係などの情報です。
- `document.zip`：EDINET が提供する XBRL／Inline XBRL ファイル一式です。
- `document.pdf`：EDINET が提供する PDF です。PDF が存在する場合だけダウンロードします。

ZIP ファイル名だけでは書類種別を判別できません。原本の報告書か訂正報告書かを判定するには、`metadata.json` の `docTypeCode` と `parentDocID` を参照します。

## 実行方法

EDINET API キーはソースコードに記述せず、ローカルの環境変数に設定します。

```bash
export EDINET_API="your-api-key"
```

プロジェクトディレクトリで次のコマンドを実行します。

```bash
uv run python download_raw.py 2024-01-01 2024-12-31
```

日付引数はどちらも省略できます。日付を指定しない場合は、当日までの直近5年間のデータをダウンロードします。

```bash
uv run python download_raw.py
```

ローカル Embedding とベクトルストアの追加依存関係をインストールします。

```bash
uv sync --extra local-embedding --extra vector-store
```

最初の実行時に `cl-nagoya/ruri-v3-310m` が Hugging Face からローカルキャッシュへダウンロードされます。モデルファイルは約 1.27 GB で、API 利用料は発生しません。

```python
from finrag.processing.embedding import embed_chunks
from finrag.processing.ruri_embedding_client import RuriEmbeddingClient

client = RuriEmbeddingClient()
embedded_chunks = embed_chunks(document_chunks, client, batch_size=100)
query_vector = client.embed_query("主要な事業リスクは何ですか？")
```

OpenAI を代替バックエンドとして使う場合のみ、`OPENAI_API_KEY` 環境変数を設定します。

### ベクトルの保存と検索

Qdrant Local のデータは `data/vector_store/qdrant/` に保存します。`chunk_id` が同じデータを再度保存すると、重複を作らず既存データを更新します。

```python
from datetime import date
from pathlib import Path

from finrag.storage.qdrant_vector_store import QdrantVectorStore
from finrag.storage.vector_store import SearchFilters

store = QdrantVectorStore(Path("data/vector_store/qdrant"))
try:
    store.upsert(embedded_chunks)
    results = store.search(
        query_vector,
        filters=SearchFilters(
            edinet_code="E02655",
            period_end=date(2024, 3, 31),
            document_type="annual_securities_report",
        ),
        top_k=5,
    )
finally:
    store.close()
```

各検索結果には類似度、本文、企業、書類、章、会計期間、出典ファイルが含まれます。

## 現在の対象範囲

現在のコードは元ファイルのダウンロード、書類識別、XBRL 本文の抽出、章構造化、検索用チャンクの作成、Embedding の生成、ローカルのベクトル保存と検索を担当しています。次の機能はまだ実装されていません。

- 実データの検索品質評価
- RAG 回答生成
- CI による自動テスト実行
