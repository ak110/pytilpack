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

`pyproject.toml`の`[tool.uv] override-dependencies`による上書きは本リポジトリの依存解決にのみ適用され、
配布物のメタデータには含まれない。
上流パッケージの厳密ピンにより依存更新だけでは問題を解消できない場合、上書きによる迂回の採否は
当該の依存が配布物のメタデータを経由して利用者環境へ波及するかで分ける。
`[project.dependencies]`と`[project.optional-dependencies]`が宣言する依存、および
それらから推移的に解決される依存は利用者環境へ波及する。
これらを上書きで迂回しても利用者環境では未解消のまま残り、本リポジトリの依存解決だけが健全な状態になる。
実態と乖離した状態を残さないため当該の迂回は行わない。
上流パッケージ側がピンを追従するのを待ち、迂回しない判断の根拠と解除条件を該当箇所のコメントへ残す。
一方、開発用の依存グループ経由でのみ入る依存のピンは利用者環境へ波及しないため、上書きで迂回してよい。
迂回の理由と解除条件を該当箇所のコメントへ残す。

`pyproject.toml`の`dependencies`または`override-dependencies`でパッケージの版指定を変更した場合、
`uv lock`・`uv sync`・`uv run`の成功だけでは配布経路の成立を確認できない。
上書き設定が適用されない状態で依存解決が成立することを
`uvx --exclude-newer "1 day" --from . pytilpack --help`で実測する。
当該コマンドは利用者環境と同じ経路で配布物の依存を解決するため、
上書き設定に依存した版指定を検出できる。
`uvx`は`pyproject.toml`の`[tool.uv]`を読まないため`exclude-newer`が適用されない。
公開待機を維持するため`--exclude-newer`を明示する。
当該コマンドが解決するのは配布物のメタデータが宣言する実行時依存に限る。
開発用の依存グループだけに適用される上書きは観測できない。
`make test`は`uvx`が解決する独立した環境で検査ツールを起動するため、
配布経路の依存解決を経由せず当該不整合も検出しない。
実測が失敗した場合は原因を確認する。
通信障害・パッケージ索引の障害・ビルド環境の不備など、版指定以外の原因を解消して再実測する。
変更した版指定に起因する依存解決不能を確認した場合は、配布物のインストールを不能にするため
当該版指定を採用しない。

`override-dependencies`の追加・変更は開発環境の依存解決にも影響する。
上書きにより開発用の依存グループが要求する版が満たされなくなると、当該の依存へ依存する
開発用ツールが起動しなくなる。前段のどの手順もこの不成立を観測しない。
上書きを追加または変更した場合は、`uv lock`で変更をロックファイルへ反映したうえで、
上書き対象のパッケージへ依存する開発用ツールを`uv run --locked <ツール名> --help`のような
軽量な指定で起動し、終了コードが0であることを実測する。
`--locked`は`uv.lock`が変更されないことを表明する指定であり、
ロックファイルへ未反映の変更が残っている場合に実測を失敗させる。
起動しない状態を許容する場合は、影響範囲・許容する理由・解除条件を
`pyproject.toml`の当該`override-dependencies`のコメントへ残す。

### MCP SDK 2.0.0以上への移行

コア依存の`mcp`は2.0.0以上を要求する。コア依存の版指定には、原則として上限を設けない。経緯と根拠は次のとおり。

- 2.0.0では`mcp.server.fastmcp`を削除して`mcp.server.mcpserver`へ改称し、互換のための別名を提供しない。
  `pytilpack/cli/mcp.py`は改称後の`MCPServer`を使う。1.x系では動作しないため下限を`2.0.0`とする
- 2.0.0は`httpx2`・`mcp-types`・`starlette`・`uvicorn`・`pydantic`・`pyjwt`・`opentelemetry-api`・
  `jsonschema`・`python-multipart`・`sse-starlette`をコア依存として要求する。
  `mcp`は本リポジトリのコア依存であるため、これらが全利用者へ無条件で入る。
  MCPサーバー機能を`pip install pytilpack`だけで利用できる状態を保つ判断として当該増加を受け入れた
- 移行前は1.x系へ据え置き`<2`の上限を設けていたが、上限を引き上げる契機が運用上存在せず、
  上限が放置される。コア依存の版指定へ原則として上限を設けない方針へ改め、`werkzeug`の上限も併せて撤廃した
- 上流のメジャー更新で`pytilpack/cli/mcp.py`のimportが失敗しても、
  サブコマンド登録は当該サブコマンドのみを利用不可として扱い、CLI全体の起動は継続する

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
