# 技術コンテキスト

## 必須要件

### Python環境

- Python 3.11以上
- 型ヒント完全対応
- asyncio対応

### 開発ツール

- uv: パッケージ管理
- pre-commit: コード品質管理
- pytest: テストフレームワーク
- black/isort: コードフォーマット

### CI/CD

- GitHub Actions
- PyPI自動デプロイ

## 依存関係

### 基本パッケージ

```text
typing-extensions>=4.0
```

### オプショナルパッケージ

```text
fastapi>=0.111
flask>=3.0
quart>=0.20.0
openai>=1.25
tiktoken>=0.6
sqlalchemy>=2.0
```

### 開発用パッケージ

```text
pyfltr>=1.6.0
pytest-asyncio>=0.21.0
types-markdown>=3.7.0
types-pyyaml>=6.0.12
```

## セキュリティ要件

- 安全なエラー処理
- 適切な例外処理
- セキュアなデフォルト設定

## パフォーマンス要件

- 非同期処理の最適化
- メモリ使用量の管理
- 効率的なリソース利用
