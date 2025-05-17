# プロジェクト概要

## 目的

pytilpack は、Python の各種ライブラリのユーティリティ集を提供するプロジェクトです。

## コア機能

- 標準ライブラリの拡張機能（asyncio_, pathlib_, base64_等）
- WebフレームワークのユーティリティAPI（FastAPI, Flask, Quart）
- データ処理機能（JSON, YAML, CSV, HTML RAG等）
- AIツール連携（OpenAI, tiktoken）

## 技術スタック

- Python 3.11以上
- uv: パッケージ管理
- pre-commit: コード品質管理
- GitHub Actions: CI/CD

## プロジェクト規約

- black/isortによる一貫したコードスタイル
- 型ヒントの完全サポート
- pytestによる単体テスト
- Markdown形式のドキュメント
