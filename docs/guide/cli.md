# CLIコマンド

一部機能はCLIから利用できる。

## uvx から起動する場合

`uvx pytilpack` はベースパッケージのみで起動する。`mcp` や `fetch` はベース依存で動作するためそのまま実行できる。`wait-for-db-connection` や `babel` のように追加依存を必要とするサブコマンドは `--from` で必要なextrasを明示する。

```bash
uvx pytilpack mcp
uvx pytilpack fetch https://example.com/
uvx --from 'pytilpack[sqlalchemy]' pytilpack wait-for-db-connection "$SQLALCHEMY_DATABASE_URI"
uvx --from 'pytilpack[babel]' pytilpack babel extract .
```

extrasが足りない状態で該当サブコマンドを呼ぶと、必要なextras名を含むエラーメッセージが表示される。

## 空のディレクトリを削除

```bash
pytilpack delete-empty-dirs path/to/dir [--no-keep-root] [--verbose]
```

- 空のディレクトリを削除
- デフォルトでルートディレクトリを保持（`--no-keep-root`で削除可能）

## 古いファイルを削除

```bash
pytilpack delete-old-files path/to/dir --days=7 \
  [--no-delete-empty-dirs] [--no-keep-root-empty-dir] [--verbose]
```

- 指定した日数より古いファイルを削除（`--days`オプションで指定）
- デフォルトで空ディレクトリを削除（`--no-delete-empty-dirs`で無効化）
- デフォルトでルートディレクトリを保持（`--no-keep-root-empty-dir`で削除可能）

## ディレクトリを同期

```bash
pytilpack sync src dst [--delete] [--verbose]
```

- コピー元（src）からコピー先(dst)へファイル・ディレクトリを同期
- 日付が異なるファイルをコピー
- `--delete`オプションでコピー元に存在しないコピー先のファイル・ディレクトリを削除

## URLの内容を取得

```bash
pytilpack fetch url [--no-verify] [--accept=CONTENT_TYPE] \
  [--user-agent=USER_AGENT] [--verbose]
```

- URLからHTMLを取得し、簡略化して標準出力に出力
- `--no-verify`オプションでSSL証明書の検証を無効化
- `--accept`オプションで受け入れるコンテンツタイプを指定
- `--user-agent`オプションでUser-Agentヘッダーを指定
- `--verbose`オプションで詳細なログを出力

## MCPサーバーを起動

```bash
pytilpack mcp [--transport=stdio] [--host=localhost] [--port=8000] [--verbose]
```

- Model Context ProtocolサーバーとしてpytilpackのFetch機能を提供
- `--transport`オプションで通信方式を指定（stdio/http、デフォルト: stdio）
- `--host`オプションでサーバーのホスト名を指定（httpの場合のみ使用、デフォルト: localhost）
- `--port`オプションでサーバーのポート番号を指定（httpの場合のみ使用、デフォルト: 8000）
- `--verbose`オプションで詳細なログを出力

### stdioモード

```bash
pytilpack mcp
# または
pytilpack mcp --transport=stdio
```

### httpモード

```bash
pytilpack mcp --transport=http --port=8000
```

## Babelメッセージ管理

```bash
pytilpack babel extract input_dirs... [-o messages.pot] [-k KEYWORDS...] [--charset=utf-8]
pytilpack babel init -l LOCALE [-i messages.pot] [-d locales] [--domain=messages]
pytilpack babel update [-i messages.pot] [-d locales] [--domain=messages]
pytilpack babel compile [-d locales] [--domain=messages]
```

- gettextメッセージの抽出、初期化、更新、コンパイルを行う
- `extract`: 指定ディレクトリからメッセージを抽出してPOTファイルに出力
- `init`: POTファイルから新しいロケールのカタログを初期化
- `update`: 既存カタログをテンプレートで更新
- `compile`: POファイルをコンパイルしてMOファイルを生成

## DB接続待機

```bash
pytilpack wait-for-db-connection SQLALCHEMY_DATABASE_URI [--timeout=180] [--verbose]
```

- 指定されたSQLALCHEMY_DATABASE_URIで、DB接続が可能になるまで待機
- URLに非同期ドライバ（`+asyncpg`, `+aiosqlite`, `+aiomysql`等）が含まれる場合は自動で非同期処理を使用
- `--timeout`オプションでタイムアウト秒数を指定（デフォルト: 180）
- `--verbose`オプションで詳細なログを出力
