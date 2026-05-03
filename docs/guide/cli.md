# CLIコマンド

一部機能はCLIから利用できる。

## uvxから起動する場合

`uvx pytilpack`はベースパッケージのみで起動する。
`mcp`や`fetch`はベース依存で動作するためそのまま実行できる。
`wait-for-db-connection`や`babel`のように追加依存を必要とするサブコマンドは`--from`で必要なextrasを明示する。

```bash
uvx pytilpack mcp
uvx pytilpack fetch https://example.com/
uvx --from='pytilpack[sqlalchemy]' pytilpack wait-for-db-connection "$SQLALCHEMY_DATABASE_URI"
uvx --from='pytilpack[babel]' pytilpack babel extract .
```

extrasが足りない状態で該当サブコマンドを呼ぶと、必要なextras名を含むエラーメッセージが表示される。

## 空のディレクトリを削除

```bash
pytilpack delete-empty-dirs path/to/dir [--no-keep-root] [--verbose]
```

空のディレクトリを削除する。デフォルトでルートディレクトリを保持する。

## 古いファイルを削除

```bash
pytilpack delete-old-files path/to/dir --days=7 [--no-delete-empty-dirs] [--verbose]
```

指定した日数より古いファイルを削除する。デフォルトで空ディレクトリも削除する。

## ディレクトリを同期

```bash
pytilpack sync src dst [--delete] [--verbose]
```

コピー元からコピー先へファイル・ディレクトリを同期する。
`--delete`でコピー元に存在しないコピー先のファイル・ディレクトリを削除する。

## URLの内容を取得

```bash
pytilpack fetch url [--no-verify] [--accept=CONTENT_TYPE] [--user-agent=USER_AGENT] [--verbose]
```

URLからHTMLを取得し、簡略化して標準出力に出力する。

## MCPサーバーを起動

```bash
pytilpack mcp [--transport=stdio|http] [--host=localhost] [--port=8000] [--verbose]
```

Model Context ProtocolサーバーとしてpytilpackのFetch機能を提供する。
`--transport`でstdio（デフォルト）またはhttp通信方式を選択できる。

## Babelメッセージ管理

```bash
pytilpack babel extract input_dirs... [-o messages.pot] [-k KEYWORDS...]
pytilpack babel init -l LOCALE [-i messages.pot] [-d locales]
pytilpack babel update [-i messages.pot] [-d locales]
pytilpack babel compile [-d locales]
```

gettextメッセージの抽出・初期化・更新・コンパイルを行う。

## DB接続待機

```bash
pytilpack wait-for-db-connection SQLALCHEMY_DATABASE_URI [--timeout=180] [--verbose]
```

指定URIでDB接続が可能になるまで待機する（デフォルトタイムアウト: 180秒）。
非同期ドライバ（`+asyncpg`、`+aiosqlite`等）を含むURIの場合は自動で非同期処理を使用する。
