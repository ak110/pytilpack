# CLAUDE.md: pytilpack

## 開発手順

- `make update`: 依存更新 + pre-commit autoupdate + pinactアクション更新 + 全テスト実行
  - `make update-actions`: GitHub Actionsのハッシュピン更新のみ（mise経由でpinact実行）
- リリース手順: [docs/development/development.md](docs/development/development.md) 参照
- テストコードは`pytilpack/xxx.py`に対して`tests/xxx_test.py`として配置する
  - `pytilpack/xxx/yyy.py`に対して`tests/xxx/yyy_test.py`
  - `xxx`がpythonキーワードなどの場合、`xxx_.py`になる。そのときは`xxx_test.py`とする（アンダースコアは対象外）
- コミット前の検証方法: `uv run pyfltr run-for-agent`
  - ドキュメントなどのみの変更の場合は省略可（pre-commitで実行されるため）
  - テストコードの単体実行なども極力 `uv run pyfltr run-for-agent <path>` を使う（pytestを直接呼び出さない）
    - 詳細な情報などが必要な場合に限り `uv run pytest -vv <path>` などを使用
  - 修正後の再実行時は、対象ファイルや対象ツールを必要に応じて絞って実行する（最終検証はCIに委ねる前提）
    - 例: `pyfltr run-for-agent --commands=mypy,ruff-check path/to/file`

## 注意点

- コア依存（`[project.dependencies]`）は最小限に保つ（現在: `beautifulsoup4`/`httpx`/`mcp`/`werkzeug`）
- サードパーティライブラリに依存するモジュールはextras（`[project.optional-dependencies]`）で管理する
- インポートは原則トップレベルで行う（`.pylintrc` で `import-outside-toplevel` は有効）
- モジュール追加時は必ず`/add-module`スキルを使用する
