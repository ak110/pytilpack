# プロジェクト概要

## 目的

pytilpack は、Python の各種ライブラリのユーティリティ集を提供するプロジェクトです。開発者が一般的なタスクを効率的に実行できるように、様々なライブラリに関連する便利な機能をまとめています。

## コア要件

- 各種 Python ライブラリのユーティリティ関数の提供
- モジュール化された構造による機能の整理
- 柔軟なインストールオプション（最小限のインストールから全機能のインストールまで）

## スコープ

### 含まれるもの

- 標準ライブラリのユーティリティ（asyncio, csv, pathlib 等）
- 一般的なフレームワークのユーティリティ（FastAPI, Flask, Quart 等）
- データ処理関連のユーティリティ（JSON, YAML 等）
- Web 関連のユーティリティ（HTML RAG, データ URL 等）

### 含まれないもの

- 個別のライブラリの完全な置き換え
- 過度に特殊化された機能
- 実験的な機能の実装

## 成功指標

- コードスタイルの一貫性（black によるフォーマット）
- 継続的なテストの成功
- PyPI での安定したリリース
- 明確なドキュメント化された機能
