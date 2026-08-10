# fin-rag-engine

日本の EDINET 開示書類を対象とした RAG データ処理プロジェクトです。現在は第1段階として、企業と期間を指定して EDINET を検索し、有価証券報告書および訂正有価証券報告書の元データを保存する機能を実装しています。

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
│       └── processing/
│           ├── __init__.py
│           └── chunker.py
├── tests/
│   ├── test_chunker.py
│   ├── test_edinet.py
│   ├── test_identifier.py
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
| `tests/test_chunker.py` | チャンクの長さ、重複部分、メタデータの引継ぎを検証します。 |
| `tests/test_edinet.py` | EDINET ダウンロード機能のテストファイルです。現在、テストはまだ追加されていません。 |
| `tests/test_identifier.py` | 書類識別と訂正報告書の選択ルールを検証します。 |
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

## 現在の対象範囲

現在のコードは元ファイルのダウンロード、書類識別、XBRL 本文の抽出、章構造化、検索用チャンクの作成を担当しています。次の機能はまだ実装されていません。

- ベクトル化、ベクトルデータベース、RAG 検索
- 一連の自動テスト
