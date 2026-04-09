# pytilpack

Pythonのユーティリティ集。

[![CI](https://github.com/ak110/pytilpack/actions/workflows/ci.yaml/badge.svg)](https://github.com/ak110/pytilpack/actions/workflows/ci.yaml)
[![PyPI version](https://badge.fury.io/py/pytilpack.svg)](https://badge.fury.io/py/pytilpack)

## インストール

ベースパッケージ（stdlib系ユーティリティ + httpx/werkzeug）:

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

`uvx` でCLIを使う場合、サブコマンドが要求するextrasを `--from` で明示する:

```bash
uvx --from 'pytilpack[mcp]' pytilpack mcp
uvx --from 'pytilpack[sqlalchemy]' pytilpack wait-for-db-connection "$SQLALCHEMY_DATABASE_URI"
```

### extras 一覧

| Extra | 対象モジュール | 主な依存パッケージ |
| ----- | -------------- | ------------------ |
| `all` | 全モジュール | (全依存) |
| `babel` | `pytilpack.babel`, `pytilpack.i18n` | babel |
| `bleach` | (markdown extraに含まれる) | bleach |
| `environ` | `pytilpack.environ` | python-dotenv |
| `fastapi` | `pytilpack.fastapi` | fastapi, html5lib |
| `flask` | `pytilpack.flask`, `pytilpack.flask_login` | flask, flask-login, html5lib |
| `htmlrag` | `pytilpack.htmlrag` | beautifulsoup4 |
| `markdown` | `pytilpack.markdown` | bleach, markdown, tinycss2 |
| `mcp` | CLI: `pytilpack mcp` | mcp, beautifulsoup4 |
| `msal` | `pytilpack.msal` | azure-identity, cryptography, msal |
| `pycryptodome` | `pytilpack.pycrypto` | pycryptodome |
| `pydantic` | `pytilpack.pydantic` | pydantic |
| `pytest` | `pytilpack.pytest` | pytest, pytest-asyncio |
| `pyyaml` | `pytilpack.yaml` | pyyaml |
| `quart` | `pytilpack.quart`, `pytilpack.quart_auth` | quart, quart-auth, hypercorn, uvicorn |
| `sqlalchemy` | `pytilpack.sqlalchemy` | sqlalchemy, tabulate |
| `tiktoken` | `pytilpack.tiktoken` | tiktoken, openai, pillow |
| `tqdm` | `pytilpack.tqdm` | tqdm |
| `web` | `pytilpack.web` (check_html) | html5lib |

## 主な使い方

各モジュールを個別にimportして利用する。

```python
import pytilpack.xxx
```

`xxx` には対象ライブラリ名（`httpx` や `pathlib` など）が入る。

一部はCLIもある。詳細は [CLIコマンド](cli.md) を参照。

## 各種ライブラリ用ユーティリティ

- [pytilpack.asyncio](api/asyncio.md)
- [pytilpack.babel](api/babel.md)
- [pytilpack.base64](api/base64.md)
- [pytilpack.csv](api/csv.md)
- [pytilpack.dataclasses](api/dataclasses.md)
- [pytilpack.datetime](api/datetime.md)
- [pytilpack.fastapi](api/fastapi.md)
- [pytilpack.flask](api/flask.md)
- [pytilpack.flask_login](api/flask_login.md)
- [pytilpack.fnctl](api/fnctl.md)
- [pytilpack.functools](api/functools.md)
- [pytilpack.httpx](api/httpx.md)
- [pytilpack.importlib](api/importlib.md)
- [pytilpack.json](api/json.md)
- [pytilpack.logging](api/logging.md)
- [pytilpack.markdown](api/markdown.md)
- [pytilpack.msal](api/msal.md)
- [pytilpack.pathlib](api/pathlib.md)
- [pytilpack.pycrypto](api/pycrypto.md)
- [pytilpack.pydantic](api/pydantic.md)
- [pytilpack.pytest](api/pytest.md)
- [pytilpack.python](api/python.md)
- [pytilpack.quart](api/quart.md)
- [pytilpack.quart_auth](api/quart_auth.md)
- [pytilpack.sqlalchemy](api/sqlalchemy.md)
- [pytilpack.threading](api/threading.md)
- [pytilpack.threadinga](api/threadinga.md): asyncio版
- [pytilpack.tiktoken](api/tiktoken.md)
- [pytilpack.tqdm](api/tqdm.md)
- [pytilpack.typing](api/typing.md)
- [pytilpack.yaml](api/yaml.md)

## 特定ライブラリに依存しないモジュール

- [pytilpack.cache](api/cache.md): ファイルキャッシュ関連
- [pytilpack.crypto](api/crypto.md): 署名・トークン関連
- [pytilpack.data_url](api/data_url.md): データURL関連
- [pytilpack.environ](api/environ.md): 環境変数関連
- [pytilpack.healthcheck](api/healthcheck.md): ヘルスチェック処理関連
- [pytilpack.htmlrag](api/htmlrag.md): HtmlRAG関連
- [pytilpack.http](api/http.md): HTTP関連
- [pytilpack.i18n](api/i18n.md): 国際化(i18n)関連
- [pytilpack.io](api/io.md): IO関連のユーティリティ
- [pytilpack.jsonc](api/jsonc.md): JSON with Comments関連
- [pytilpack.paginator](api/paginator.md): ページネーション関連
- [pytilpack.random](api/random.md): 疑似乱数関連
- [pytilpack.ratelimit](api/ratelimit.md): レートリミッター
- [pytilpack.secrets](api/secrets.md): シークレットキー関連
- [pytilpack.sse](api/sse.md): Server-Sent Events関連
- [pytilpack.validator](api/validator.md): バリデーション関連
- [pytilpack.web](api/web.md): Web関連
