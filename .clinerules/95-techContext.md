# 技術コンテキスト

## 開発環境

### 必須ツール

- Python: 3.11以上
- uv: パッケージ管理ツール
- pre-commit: コミット前の自動チェック
- black: コードフォーマッター
- GitHub CLI (gh): リリース管理用

### 開発ツール設定

```toml
# pyproject.toml の主要な設定
[project]
name = "pytilpack"
requires-python = ">=3.11,<4.0"
dependencies = ["typing-extensions>=4.0"]

[tool.black]
target-version = ['py311']
skip-magic-trailing-comma = true

[tool.pyfltr]
pyupgrade-args = ["--py311-plus"]
pylint-args = ["--jobs=4"]

[tool.isort]
profile = "black"

[tool.pytest.ini_options]
addopts = "--showlocals -p no:cacheprovider --durations=5 -vv"
xfail_strict = true
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "module"

[tool.mypy]
allow_redefinition = true
check_untyped_defs = true
ignore_missing_imports = true
strict_optional = true
strict_equality = true
warn_no_return = true
warn_redundant_casts = true
warn_unused_configs = true
show_error_codes = true
```

## 使用技術

### コア技術

- **Python標準ライブラリ**
  - asyncio: 非同期処理
  - pathlib: ファイル操作
  - threading: マルチスレッド
  - logging: ログ管理
  - datetime: 日付処理

### Webフレームワーク

- FastAPI: >=0.111
- Flask: >=3.0
- Quart: >=0.20.0

### データ処理

- JSON/YAML: データシリアライズ
- HTML: RAG処理
- Polars: テーブルデータ処理

### 開発支援

- pytest: テストフレームワーク
- GitHub Actions: CI/CD
- pre-commit hooks: コード品質管理

## 依存関係管理

### 基本パッケージ

```text
typing-extensions>=4.0
```

### オプショナルパッケージ

```text
bleach>=6.2
beautifulsoup4>=4.12
fastapi>=0.111
flask>=3.0
flask-login>=0.6
html5lib
httpx
markdown>=3.6
openai>=1.25
pillow
pytest
pytest-asyncio
pyyaml>=6.0
quart>=0.20.0
sqlalchemy>=2.0
tabulate[widechars]>=0.9
tiktoken>=0.6
tinycss2>=1.4
tqdm>=4.0
```

### 開発用パッケージ

```text
aiosqlite>=0.21.0
pyfltr>=1.6.0
pytest-asyncio>=0.21.0
types-bleach>=6.2.0.20241123
types-markdown>=3.7.0.20241204
types-pyyaml>=6.0.12.20241230
types-tabulate>=0.9.0.20241207
```

## セットアップ手順

### 1. 開発環境構築

```bash
# uvのインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# pre-commitのインストール
pip install pre-commit
pre-commit install

# 依存関係のインストール
uv pip install -e ".[all]"
```

### 2. テスト環境

```bash
# テストの実行
uv run pytest
```

### 3. リリース環境

```bash
# GitHub CLIのセットアップ
gh auth login

# リリースの作成
gh release create --target=master --generate-notes vX.X.X
```

## 技術的制約

### 互換性要件

- Python 3.11以上のサポート
- 各依存ライブラリの最新安定版との互換性維持
- 型ヒントの完全サポート

### パフォーマンス考慮事項

- 非同期処理の適切な使用
- メモリ使用量の最適化
- 不要な依存関係の回避

### セキュリティ要件

- 安全なエラー処理
- 適切な例外処理
- セキュアなデフォルト設定

## 監視と保守

### ログ管理

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
```

### エラー追跡

- 詳細なエラーメッセージ
- スタックトレースの保持
- デバッグ情報の提供

### パフォーマンス監視

- テストの実行時間
- メモリ使用量
- 依存関係の影響
