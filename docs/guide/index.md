# 利用者向けガイド

## インストール

標準ライブラリ用の支援と、ベース依存を使うモジュールを導入する:

コア依存: `beautifulsoup4`、`httpx`、`mcp`、`werkzeug`。

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
| `all` | 全モジュール | `azure-identity`、`babel`、`bleach`、`cryptography`、`defusedxml`、`fastapi`、`flask-login`、`flask`、`html5lib`、`hypercorn`、`markdown`、`msal`、`openai`、`pillow`、`pycryptodome`、`pydantic`、`pytest`、`pytest-asyncio`、`python-dotenv`、`pyyaml`、`quart-auth`、`quart`、`sqlalchemy[asyncio]`、`tabulate[widechars]`、`tiktoken`、`tinycss2`、`tqdm`、`uvicorn` |
| `babel` | `pytilpack.babel` | `babel` |
| `bleach` | `bleach` | `bleach` |
| `environ` | `pytilpack.environ` | `python-dotenv` |
| `fastapi` | `pytilpack.fastapi` | `defusedxml`、`fastapi`、`html5lib` |
| `flask` | `pytilpack.flask`、`pytilpack.flask_login` | `defusedxml`、`flask-login`、`flask`、`html5lib` |
| `htmlrag` | `pytilpack.htmlrag`（ベース依存で利用可能） | なし（後方互換用の空extra） |
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

### Webフレームワーク

- [pytilpack.fastapi](../api/fastapi.md)
- [pytilpack.flask](../api/flask.md)
- [pytilpack.flask_login](../api/flask_login.md)
- [pytilpack.quart](../api/quart.md)
- [pytilpack.quart_auth](../api/quart_auth.md)

### データ処理・シリアライゼーション

- [pytilpack.csv](../api/csv.md)
- [pytilpack.dataclasses](../api/dataclasses.md)
- [pytilpack.json](../api/json.md)
- [pytilpack.jsonc](../api/jsonc.md): JSON with Comments関連
- [pytilpack.pydantic](../api/pydantic.md)
- [pytilpack.sqlalchemy](../api/sqlalchemy.md)
- [pytilpack.yaml](../api/yaml.md)

### セキュリティ・暗号

- [pytilpack.crypto](../api/crypto.md): 署名・トークン関連
- [pytilpack.msal](../api/msal.md)
- [pytilpack.pycrypto](../api/pycrypto.md): AES-GCM暗号化
- [pytilpack.secrets](../api/secrets.md): シークレットキー関連

### HTTP・Web

- [pytilpack.data_url](../api/data_url.md): データURL関連
- [pytilpack.healthcheck](../api/healthcheck.md): ヘルスチェック処理関連
- [pytilpack.htmlrag](../api/htmlrag.md): HtmlRAG関連
- [pytilpack.http](../api/http.md): HTTP関連
- [pytilpack.httpx](../api/httpx.md)
- [pytilpack.sse](../api/sse.md): Server-Sent Events関連
- [pytilpack.web](../api/web.md): Web関連

### 国際化・テキスト処理

- [pytilpack.babel](../api/babel.md)
- [pytilpack.base64](../api/base64.md)
- [pytilpack.i18n](../api/i18n.md): 国際化(i18n)関連（ベース依存で利用可能）
- [pytilpack.markdown](../api/markdown.md)
- [pytilpack.tiktoken](../api/tiktoken.md)

### 非同期・並行処理

- [pytilpack.asyncio](../api/asyncio.md)
- [pytilpack.ratelimit](../api/ratelimit.md): レートリミッター
- [pytilpack.threading](../api/threading.md)
- [pytilpack.threadinga](../api/threadinga.md): asyncio版スレッドユーティリティ

### ファイルシステム・OS

- [pytilpack.cache](../api/cache.md): ファイルキャッシュ関連
- [pytilpack.fnctl](../api/fnctl.md)
- [pytilpack.io](../api/io.md): IO関連のユーティリティ
- [pytilpack.pathlib](../api/pathlib.md)
- [pytilpack.zipfile](../api/zipfile.md): ZIPエントリ名復号、Zip Slip検証

### 開発・テスト支援

- [pytilpack.datetime](../api/datetime.md)
- [pytilpack.environ](../api/environ.md): 環境変数関連
- [pytilpack.functools](../api/functools.md)
- [pytilpack.importlib](../api/importlib.md)
- [pytilpack.logging](../api/logging.md)
- [pytilpack.paginator](../api/paginator.md): ページネーション関連
- [pytilpack.pytest](../api/pytest.md)
- [pytilpack.python](../api/python.md)
- [pytilpack.random](../api/random.md): 疑似乱数関連
- [pytilpack.tqdm](../api/tqdm.md)
- [pytilpack.typing](../api/typing.md)
- [pytilpack.validator](../api/validator.md): バリデーション関連
