# カスタム指示 (プロジェクト固有)

- `pyproject.toml` の依存関係編集は極力 `uv` コマンドを使う (`uv add`, `uv remove` など)
  - 手動編集は `uv` コマンドでは対応できない箇所に限る

## 開発コマンド

- .venvの更新には`make update`を使う
- コードを書いた後は必ず`make format`で整形する
  - 新しいファイルを作成する場合は近い階層の代表的なファイルを確認し、可能な限りスタイルを揃える
- `make test`でmypy, pytestなどをまとめて実行できる
- `make update`: 依存更新 + pre-commit autoupdate + 全テスト実行
- pyfltr は git ソースなので更新時は `uv lock --upgrade-package pyfltr && uv sync` が必要
- テストコードは`pytilpack/xxx.py`に対して`tests/xxx_test.py`として配置する
  - `pytilpack/xxx/yyy.py`に対して`tests/xxx/yyy_test.py`
  - `xxx`がpythonキーワードなどの場合、`xxx_.py`になる。そのときは`xxx_test.py`とする (アンダースコアは無視)
- テストコードの実行は `uv run pyfltr <path>` を使う (pytestを直接呼び出さない)
  - `-vv`などが必要な場合に限り `uv run pyfltr -vv <path>` のようにする
- Markdownファイルのformat/lintの実行方法: `uv run pre-commit run --files <file>`

## 依存関係の方針

- コア依存 (`[project.dependencies]`) は最小限に保つ (現在: httpx, typing-extensions, werkzeug)
- サードパーティライブラリに依存するモジュールは extras (`[project.optional-dependencies]`) で管理する
- インポートは原則トップレベルで行う (`.pylintrc` で `import-outside-toplevel` は有効)

### モジュール追加時の extras チェックリスト

新しいモジュール `pytilpack/xxx.py` がサードパーティライブラリに依存する場合:

1. `pyproject.toml` に extras を追加: `uv add --optional xxx library`
2. `[all]` extras にも同じパッケージを追加: `uv add --optional all library`
3. 推移的依存に注意: 他の pytilpack モジュールを import している場合、そのモジュールの依存も extras に含める
4. `docs/api/xxx.md` に `!!! note "必要なextra"` 注記を追加
5. `README.md` と `docs/index.md` の extras 一覧テーブルを更新

## 関連ドキュメント

- @README.md
- @docs/README.md
- @docs/development.md
- モジュール追加時は `docs/index.md` と `docs/api/xxx.md` の更新要
- ドキュメント追加時は `mkdocs.yml` の `nav` 更新要
