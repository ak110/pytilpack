# 開発手順

## 開発環境の構築手順

1. 本リポジトリをcloneする
2. セットアップを実行する

    ```bash
    make setup
    ```

## 開発コマンド

| コマンド | 用途 |
| --- | --- |
| `make format` | 整形 + 軽量lint + 自動修正（開発時の手動実行用） |
| `make test` | 全チェック実行（コミット前の最終確認用） |
| `make update` | 依存更新 |
| `make docs` | ドキュメントのローカルプレビュー（`http://127.0.0.1:8000/`） |

## サプライチェーン攻撃対策

ロックファイル尊重・公開待機・ピン留め運用の3点を基本方針とする。

- `uv.lock`をそのまま使うため`UV_FROZEN=1`を常時有効化している
- `pyproject.toml`の`exclude-newer`で公開直後パッケージの即時導入を抑制している
- GitHub Actionsは`pinact`でハッシュピン留めし、定期更新している

依存の追加・更新は`uv add`/`uv remove`/`uv lock --upgrade-package`で行う。

依存パッケージの脆弱性検知の仕組み（Dependabot alerts・定期監査ワークフロー）は設けない。
本リポジトリはライブラリであり`uv.lock`は開発専用のため、利用者の実行環境への脆弱性の影響は限定的である。

`pyproject.toml`の`dependencies`または`override-dependencies`でパッケージの版指定を変更した場合、
`uv lock`・`uv sync`・`uv run`の成功だけでは配布経路の成立を確認できない。
`override-dependencies`による上書きは本リポジトリの依存解決にのみ適用され、配布物のメタデータには含まれない。
上書き設定が適用されない状態で依存解決が成立することを
`uvx --exclude-newer "1 day" --from . pytilpack --help`で実測する。
当該コマンドは利用者環境と同じ経路で配布物の依存を解決するため、
上書き設定に依存した版指定を検出できる。
`uvx`は`pyproject.toml`の`[tool.uv]`を読まないため`exclude-newer`が適用されない。
公開待機を維持するため`--exclude-newer`を明示する。
当該コマンドが解決するのは配布物のメタデータが宣言する実行時依存に限る。
開発用の依存グループだけに適用される上書きは観測できない。
`make test`は本リポジトリの依存解決のみを用いるため当該不整合を検出しない。
実測が失敗した場合は原因を確認する。
通信障害・パッケージ索引の障害・ビルド環境の不備など、版指定以外の原因を解消して再実測する。
変更した版指定に起因する依存解決不能を確認した場合は、配布物のインストールを不能にするため
当該版指定を採用しない。

### MCP SDKを1.x系へ据え置く判断

コア依存の`mcp`は上限を設けて1.x系へ据え置き、MCP SDK 2.0系へは移行しない。根拠は次のとおり。

- 公式移行ガイド（<https://py.sdk.modelcontextprotocol.io/migration/>）は
  「If your package depends on `mcp`, keep a `<2` upper bound until you've migrated.」と記す。
  上限の維持は上流の推奨に沿う
- 2.0は`mcp.server.fastmcp`を削除して`mcp.server.mcpserver`へ改称し、互換のための別名を提供しない。
  `pytilpack/cli/mcp.py`は削除された側を直接importする
- `pytilpack/cli/main.py`のサブコマンド登録は外部パッケージ起因のimport失敗をスタブとして登録する。
  `mcp`はimport失敗時に当該サブコマンドのみ利用不可になり、CLI全体の起動は継続する。
  ただし`mcp`サブコマンド自体が利用できなくなるため、版指定上限で未然防止を継続する
- 2.0は`httpx2`・`mcp-types`・`starlette`・`uvicorn`・`pydantic`・`pyjwt`・`opentelemetry-api`・
  `jsonschema`・`python-multipart`・`sse-starlette`をコア依存として要求する。
  `mcp`は本リポジトリのコア依存であるため、これらが全利用者へ無条件で入り、
  コア依存を最小限に保つ方針と衝突する

コア依存を最小限に保つ方針を維持したまま移行するには、`mcp`をextrasへ移し、
`pytilpack/cli/main.py`のサブコマンド定義でextrasを指定する必要がある。
`pip install pytilpack`だけではmcpサブコマンドを利用できなくなるため、インストール要件の破壊的変更にあたる。
1.x系は重大な不具合修正とセキュリティパッチのみを受け取るため、当該判断は定期的に見直す。

## ドキュメントサイト運用

MkDocs + mkdocstrings + mkdocs-llmstxtでAPIリファレンスとllms.txtを自動生成し、GitHub Pagesにデプロイする。

### モジュール追加時

新しいモジュールを追加した場合は`/add-module`スキルの手順に従う。
`docs/api/<name>.md`の作成を忘れた場合はコミット時のフックおよびCIで検出される。

## リリース手順

事前に`gh`コマンドをインストールして`gh auth login`でログインし、以下のコマンドのいずれかを実行。

```bash
gh workflow run release.yaml --field="bump=PATCH"
gh workflow run release.yaml --field="bump=MINOR"
gh workflow run release.yaml --field="bump=MAJOR"
```

<https://github.com/ak110/pytilpack/actions>で状況を確認できる。
