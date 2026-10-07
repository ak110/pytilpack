# CLIコマンド

一部機能はCLIから利用できる。

## uvxから起動する場合

`uvx pytilpack`はベースパッケージのみで起動する。
`mcp`や`fetch`はベース依存で動作するためそのまま実行できる。
`wait-for-db-connection`や`babel`のように追加依存を必要とするサブコマンドは`--from`で必要なextrasを明示する。

```bash
uvx pytilpack mcp
uvx pytilpack fetch https://example.com/
uvx --from='pytilpack[sqlalchemy]' pytilpack wait-for-db-connection 'sqlite:///:memory:'
uvx --from='pytilpack[babel]' pytilpack babel extract .
```

extrasが足りない状態で該当サブコマンドを呼ぶと、必要なextras名を含むエラーメッセージが表示される。

## `pytilpack delete-empty-dirs`

空のディレクトリを削除する。ルートディレクトリは省略時に保持する。

```bash
pytilpack delete-empty-dirs ./work --verbose
pytilpack delete-empty-dirs --help
```

`--no-keep-root`で空になったルートも削除する。

## `pytilpack delete-old-files`

指定した日数より古いファイルと空ディレクトリを削除する。

```bash
pytilpack delete-old-files ./work --days=7 --verbose
pytilpack delete-old-files --help
```

`--no-delete-empty-dirs`で空ディレクトリを保持する。

## `pytilpack sync`

```bash
pytilpack sync ./source ./destination --delete --verbose
pytilpack sync --help
```

コピー元からコピー先へファイル・ディレクトリを同期する。
`--delete`でコピー元に存在しないコピー先のファイル・ディレクトリを削除する。

## `pytilpack fetch`

```bash
pytilpack fetch https://example.com/ --accept=text/html
pytilpack fetch --help
```

URLからHTMLを取得し、簡略化して標準出力に出力する。

## `pytilpack mcp`

```bash
pytilpack mcp --transport=stdio
pytilpack mcp --help
```

Model Context ProtocolサーバーとしてpytilpackのFetch機能を提供する。
`--transport`でstdio（デフォルト）またはhttp通信方式を選択できる。

## `pytilpack babel`

`pytilpack[babel]`を導入し、gettextメッセージの抽出・初期化・更新・コンパイルを行う。

```bash
pip install 'pytilpack[babel]'
pytilpack babel extract ./src -o messages.pot
pytilpack babel init -l ja -i messages.pot -d locales
pytilpack babel update -i messages.pot -d locales
pytilpack babel compile -d locales
pytilpack babel --help
```

## `pytilpack wait-for-db-connection`

`pytilpack[sqlalchemy]`を導入し、指定URIでDB接続が可能になるまで待機する。
SQLiteの標準ドライバ以外を使う場合は、URIに対応するDBドライバも同じ実行環境へ導入する。

```bash
pip install 'pytilpack[sqlalchemy]'
pytilpack wait-for-db-connection 'sqlite:///:memory:' --timeout=180 --verbose
pytilpack wait-for-db-connection --help
```

省略時の待機上限は180秒。
非同期ドライバ（`+asyncpg`、`+aiosqlite`等）を含むURIの場合は自動で非同期処理を使用する。
`sqlalchemy` extraにはこれらのDBドライバが含まれない。
たとえば`sqlite+aiosqlite`の場合は次のように`aiosqlite`も導入する。

```bash
pip install 'pytilpack[sqlalchemy]' aiosqlite
pytilpack wait-for-db-connection 'sqlite+aiosqlite:///:memory:'
uvx --from='pytilpack[sqlalchemy]' --with=aiosqlite pytilpack wait-for-db-connection 'sqlite+aiosqlite:///:memory:'
```

`postgresql+asyncpg`の場合は`asyncpg`を導入し、接続先のURIを指定する。
uvxはプロジェクトとは別の環境で動作するため、プロジェクトに導入済みでも`--with`で指定する。
ドライバは[SQLAlchemyの各DBの説明](https://docs.sqlalchemy.org/en/20/dialects/)で確認できる。
追加依存の指定は[uvのツール環境の説明](https://docs.astral.sh/uv/concepts/tools/#including-additional-dependencies)に従う。
