# 利用者向けガイド

## インストール

標準ライブラリ用の支援と、ベース依存を使うモジュールを導入する:

コア依存: `beautifulsoup4`、`httpx`、`mcp`、`werkzeug`（Windowsでは`tzdata`も導入する）。

```bash
pip install pytilpack
```

各モジュールが必要とするライブラリはextrasで追加インストールする:

```bash
pip install pytilpack[all]       # 全モジュール
pip install pytilpack[fastapi]   # pytilpack.fastapi 用
pip install pytilpack[flask]     # pytilpack.flask 用
# ...
```

Python 3.15以降では、各モジュールは関数内でだけ使う依存ライブラリを最初の利用時まで読み込まない（lazy import）。
このため必要なextrasが未導入の場合、`ImportError`がモジュールのimport時ではなく該当機能の初回呼び出し時に発生することがある。

`uvx`でCLIを使う場合、サブコマンドが要求するextrasを`--from`で明示する:

```bash
uvx pytilpack mcp
uvx --from='pytilpack[sqlalchemy]' pytilpack wait-for-db-connection 'sqlite:///:memory:'
```

SQLiteの標準ドライバ以外は、URIに対応するDBドライバも同じ環境へ導入する。
導入例は[CLIコマンドのDB接続待機](cli.md#pytilpack-wait-for-db-connection)を参照。

## extras一覧

| Extra | 対象モジュール | 直接依存パッケージ（版指定を除く） |
| --- | --- | --- |
| `all` | 全モジュール | `azure-identity`、`babel`、`bleach`、`cryptography`、`defusedxml`、`fastapi`、`filelock`、`flask-login`、`flask`、`html5lib`、`hypercorn`、`markdown`、`msal`、`openai`、`pillow`、`pycryptodome`、`pydantic`、`pytest`、`pytest-asyncio`、`python-dotenv`、`pyyaml`、`quart-auth`、`quart`、`sqlalchemy[asyncio]`、`tabulate[widechars]`、`tiktoken`、`tinycss2`、`tqdm`、`uvicorn` |
| `babel` | `pytilpack.babel` | `babel` |
| `bleach` | `bleach` | `bleach` |
| `environ` | `pytilpack.environ` | `python-dotenv` |
| `fastapi` | `pytilpack.fastapi` | `defusedxml`、`fastapi`、`html5lib` |
| `flask` | `pytilpack.flask`、`pytilpack.flask_login` | `defusedxml`、`flask-login`、`flask`、`html5lib` |
| `htmlrag` | `pytilpack.htmlrag`（ベース依存で利用可能） | なし（後方互換用の空extra） |
| `logging` | `filelock`（pytilpack.loggingのmultiprocess_file_handler用。他の機能はベース依存で利用可能） | `filelock` |
| `markdown` | `pytilpack.markdown` | `bleach`、`markdown`、`tinycss2` |
| `mcp` | `pytilpack.cli.mcp`（ベース依存で利用可能） | なし（後方互換用の空extra） |
| `msal` | `pytilpack.msal` | `azure-identity`、`cryptography`、`msal` |
| `pycryptodome` | `pytilpack.pycrypto` | `pycryptodome` |
| `pydantic` | `pytilpack.pydantic` | `pydantic` |
| `pytest` | `pytilpack.pytest` | `pytest`、`pytest-asyncio` |
| `pyyaml` | `pytilpack.yaml` | `pyyaml` |
| `quart` | `pytilpack.quart`、`pytilpack.quart_auth` | `defusedxml`、`html5lib`、`hypercorn`、`quart-auth`、`quart`、`uvicorn` |
| `sqlalchemy` | `pytilpack.sqlalchemy` | `sqlalchemy[asyncio]`、`tabulate[widechars]` |
| `tiktoken` | `pytilpack.tiktoken` | `openai`、`pillow`、`tiktoken` |
| `tqdm` | `pytilpack.tqdm` | `tqdm` |
| `web` | `pytilpack.web` | `html5lib` |

## 主な使い方

各モジュールを個別にimportして利用する。

```python
import pytilpack.xxx
```

`xxx`には対象ライブラリ名（`httpx`や`pathlib`など）が入る。

一部はCLIもある。詳細は[CLIコマンド](cli.md)を参照。

## モジュール一覧

APIの詳細は[ソースコード](https://github.com/ak110/pytilpack/tree/master/pytilpack)を読む。
`pytilpack.xxx`の実装は`pytilpack/xxx.py`または`pytilpack/xxx/`にある。

### Webフレームワーク

- `pytilpack.fastapi`
- `pytilpack.flask`
- `pytilpack.flask_login`
- `pytilpack.quart`
- `pytilpack.quart_auth`

### データ処理・シリアライゼーション

- `pytilpack.csv`
- `pytilpack.dataclasses`
- `pytilpack.json`
- `pytilpack.jsonc`: JSON with Comments関連
- `pytilpack.pydantic`
- `pytilpack.sqlalchemy`
- `pytilpack.yaml`

### セキュリティ・暗号

- `pytilpack.crypto`: 署名・トークン関連
- `pytilpack.msal`
- `pytilpack.pycrypto`: AES-GCM暗号化
- `pytilpack.secrets`: シークレットキー関連。Unix専用（ファイルロックに`fcntl`を使う）

### HTTP・Web

- `pytilpack.data_url`: データURL関連
- `pytilpack.healthcheck`: ヘルスチェック処理関連
- `pytilpack.htmlrag`: HtmlRAG関連
- `pytilpack.http`: HTTP関連
- `pytilpack.httpx`
- `pytilpack.sse`: Server-Sent Events関連
- `pytilpack.web`: Web関連

### 国際化・テキスト処理

- `pytilpack.babel`
- `pytilpack.base64`
- `pytilpack.i18n`: 国際化(i18n)関連（ベース依存で利用可能）。Babelを使う翻訳カタログ管理は`pytilpack.babel`を使う
- `pytilpack.markdown`
- `pytilpack.tiktoken`

### 非同期・並行処理

- `pytilpack.asyncio`: 実行中のイベントループから`pytilpack.asyncio.run`を呼ぶと、`coro`は別スレッドの新しいループで実行される。`coro`から親ループのリソース（SQLAlchemyの`AsyncEngine`、`asyncio.Queue`など）を参照しない
- `pytilpack.ratelimit`: レートリミッター
- `pytilpack.threading`
- `pytilpack.threadinga`: asyncio版スレッドユーティリティ

### ファイルシステム・OS

- `pytilpack.cache`: ファイルキャッシュ関連
- `pytilpack.fnctl`: Unix専用（`fcntl`を使う）
- `pytilpack.io`: IO関連のユーティリティ
- `pytilpack.pathlib`
- `pytilpack.zipfile`: ZIPエントリ名復号、Zip Slip検証

### 開発・テスト支援

- `pytilpack.datetime`
- `pytilpack.environ`: 環境変数関連
- `pytilpack.functools`
- `pytilpack.importlib`
- `pytilpack.logging`
- `pytilpack.modelcheck`: 並行処理の全ての実行順序（`ThreadExplorer`）と状態遷移の全ての到達状態（`explore_states`）を、実際のコードを呼んで確かめる補助。対象のコードは共有資源への1手順の直前で`step()`、ロックの獲得で`acquire()`か`lock()`を呼ぶ。`StepTimeoutError`を受けたら、時間切れした主体が差し替えた関数などへまだ触れうるため、同じプロセスで確認を続けずにプロセスを終えるか、隔離したプロセスで実行する
- `pytilpack.paginator`: ページネーション関連
- `pytilpack.pytest`
- `pytilpack.python`
- `pytilpack.random`: 疑似乱数関連
- `pytilpack.tqdm`
- `pytilpack.typing`
- `pytilpack.validator`: バリデーション関連
