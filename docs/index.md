# pytilpack

Pythonのユーティリティ集。

[![CI](https://github.com/ak110/pytilpack/actions/workflows/ci.yaml/badge.svg)](https://github.com/ak110/pytilpack/actions/workflows/ci.yaml)
[![PyPI version](https://badge.fury.io/py/pytilpack.svg)](https://badge.fury.io/py/pytilpack)

## インストール

```bash
pip install pytilpack
# pip install pytilpack[all]
# pip install pytilpack[anthropic]
# pip install pytilpack[fastapi]
# pip install pytilpack[flask]
# pip install pytilpack[markdown]
# pip install pytilpack[msal]
# pip install pytilpack[openai]
# pip install pytilpack[pycryptodome]
# pip install pytilpack[pytest]
# pip install pytilpack[pyyaml]
# pip install pytilpack[quart]
# pip install pytilpack[sqlalchemy]
# pip install pytilpack[tiktoken]
# pip install pytilpack[tqdm]
```

## 主な使い方

各モジュールを個別に import して利用する。

```python
import pytilpack.xxx
```

`xxx` には対象ライブラリ名（`openai` や `pathlib` など）が入る。

一部は CLI もある。詳細は [CLIコマンド](cli.md) を参照。

## 各種ライブラリ用ユーティリティ

- [pytilpack.anthropic](api/anthropic.md)
- [pytilpack.asyncio](api/asyncio.md)
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
- [pytilpack.openai](api/openai.md)
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
- [pytilpack.data_url](api/data_url.md): データURL関連
- [pytilpack.healthcheck](api/healthcheck.md): ヘルスチェック処理関連
- [pytilpack.htmlrag](api/htmlrag.md): HtmlRAG関連
- [pytilpack.http](api/http.md): HTTP関連
- [pytilpack.io](api/io.md): IO関連のユーティリティ
- [pytilpack.jsonc](api/jsonc.md): JSON with Comments関連
- [pytilpack.paginator](api/paginator.md): ページネーション関連
- [pytilpack.random](api/random.md): 疑似乱数関連
- [pytilpack.secrets](api/secrets.md): シークレットキー関連
- [pytilpack.sse](api/sse.md): Server-Sent Events関連
- [pytilpack.web](api/web.md): Web関連
