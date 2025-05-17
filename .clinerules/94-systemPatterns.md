# システムパターン

## モジュール構造

### 標準ライブラリ拡張

- xxx_.py: ライブラリ固有のユーティリティ
- xxx.py: 汎用ユーティリティ
- py.typed: 型ヒントサポート

### Webフレームワーク

- fastapi_/flask_/quart_
  - asserts.py: テスト用アサーション
  - proxy_fix.py: プロキシ対応
  - misc.py: その他機能

### CLI機能

- delete_empty_dirs.py
- delete_old_files.py

## セットアップガイド

### 開発環境構築

```bash
# uvのインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# pre-commitのインストール
pip install pre-commit
pre-commit install

# 依存関係のインストール
uv pip install -e ".[all]"
```

### テスト実行

```bash
# テストの実行
uv run pytest
```
