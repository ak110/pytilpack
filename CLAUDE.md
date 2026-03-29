# カスタム指示 (プロジェクト固有)

@CLAUDE.base.md

- `pyproject.toml` の編集は極力 `uv` コマンドを使う (`uv add`, `uv remove` など)
  - 手動編集は `uv` コマンドでは対応できない箇所に限る

## 関連ドキュメント

- @README.md
- @docs/README.md
- @docs/development.md
- @docs/style-guide.md
- モジュール追加時は `docs/index.md` と `docs/api/xxx.md` の更新要
- ドキュメント追加時は `mkdocs.yml` の `nav` 更新要
