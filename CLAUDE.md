# カスタム指示 (プロジェクト固有)

- `pyproject.toml` の依存関係編集は極力 `uv` コマンドを使う（`uv add`, `uv remove` など）
  - 手動編集は `uv` コマンドでは対応できない箇所に限る

## 開発コマンド

- `make format`: 整形 + 軽量lint + 自動修正（開発時の手動実行用）
  - 新しいファイルを作成する場合は近い階層の代表的なファイルを確認し、可能な限りスタイルを揃える
- `make test`: 全チェック実行（これが通ればコミット可能）
- `make update`: 依存更新 + pre-commit autoupdate + pinactアクション更新 + 全テスト実行
  - `make update-actions`: GitHub Actionsのハッシュピン更新のみ（mise経由でpinact実行）
- `make docs`: ドキュメントのローカルプレビュー
- テストコードは`pytilpack/xxx.py`に対して`tests/xxx_test.py`として配置する
  - `pytilpack/xxx/yyy.py`に対して`tests/xxx/yyy_test.py`
  - `xxx`がpythonキーワードなどの場合、`xxx_.py`になる。そのときは`xxx_test.py`とする（アンダースコアは対象外）
- テストコードの実行は `uv run pyfltr <path>` を使う（pytestを直接呼び出さない）
  - `-vv`などが必要な場合に限り `uv run pyfltr -vv <path>` のようにする
- Markdownファイルのformat/lintの実行方法: `uv run pre-commit run --files <file>`
- ドキュメントのみの変更（`*.md`や`docs/**`の更新）をコミットする場合、事前の手動`make test`は省略してよい。`git commit`時点で`pre-commit`の`pyfltr fast`フックが`markdownlint-fast`と`textlint-fast`を自動実行するため、Markdownの検証はそこで担保される
- コードやテストに手を入れた変更では従来どおり`make test`を通してからコミットする

## Claude Code向けコミット前検証

Claude Codeがコミット前に検証する際は、`make test`の代わりに以下を実行する。JSON Lines出力によりLLMがツール別診断を効率的に解釈できる。

```bash
uv run pyfltr run --output-format=jsonl
```

人間の開発者は従来通り`make test`を使用する。

## 依存関係の方針

- コア依存（`[project.dependencies]`）は最小限に保つ（現在: httpx, typing-extensions, werkzeug）
- サードパーティライブラリに依存するモジュールはextras（`[project.optional-dependencies]`）で管理する
- インポートは原則トップレベルで行う（`.pylintrc` で `import-outside-toplevel` は有効）
- サプライチェーン攻撃対策として`UV_FROZEN=1`を`Makefile`とCIワークフローで常時有効化し、`uv sync`/`uv run`が`uv.lock`を再resolveせずそのまま使うようにしている
  - 開発者のシェルでは`UV_FROZEN`を設定しない前提のため、依存の追加・更新は通常どおり`uv add`/`uv remove`/`uv lock --upgrade-package`を使えばよい
  - `make update`も内部で自動的にUV_FROZENを外すため、そのまま実行してよい
  - 詳細な運用方針は`docs/development/development.md`の「UV_FROZENによるlockfile尊重」セクションを参照

### モジュール追加時の extras チェックリスト

新しいモジュール `pytilpack/xxx.py` がサードパーティライブラリに依存する場合:

1. `pyproject.toml` にextrasを追加: `uv add --optional xxx library`
2. `[all]` extrasにも同じパッケージを追加: `uv add --optional all library`
3. 推移的依存に注意: 他のpytilpackモジュールをimportしている場合、そのモジュールの依存もextrasに含める
4. `docs/api/xxx.md` に `!!! note "必要なextra"` 注記を追加
5. `README.md` と `docs/index.md` のextras一覧テーブルを更新

## 関連ドキュメント

- @README.md
- @docs/index.md
- @docs/development/development.md
- モジュール追加時は `docs/index.md` と `docs/api/xxx.md` の更新要
- ドキュメント追加時は `mkdocs.yml` の `nav` 更新要
