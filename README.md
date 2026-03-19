# pytilpack

[![CI](https://github.com/ak110/pytilpack/actions/workflows/ci.yaml/badge.svg)](https://github.com/ak110/pytilpack/actions/workflows/ci.yaml)
[![PyPI version](https://badge.fury.io/py/pytilpack.svg)](https://badge.fury.io/py/pytilpack)

Pythonのユーティリティ集。

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

一部は CLI もある。詳細は [docs/cli.md](docs/cli.md) を参照。

## 各種ライブラリ用ユーティリティ

- [pytilpack.anthropic](pytilpack/anthropic.py)
- [pytilpack.asyncio](pytilpack/asyncio/__init__.py)
- [pytilpack.base64](pytilpack/base64.py)
- [pytilpack.csv](pytilpack/csv.py)
- [pytilpack.dataclasses](pytilpack/dataclasses.py)
- [pytilpack.datetime](pytilpack/datetime.py)
- [pytilpack.fastapi](pytilpack/fastapi/__init__.py)
- [pytilpack.flask](pytilpack/flask/__init__.py)
- [pytilpack.flask_login](pytilpack/flask_login.py)
- [pytilpack.fnctl](pytilpack/fnctl.py)
- [pytilpack.functools](pytilpack/functools.py)
- [pytilpack.httpx](pytilpack/httpx.py)
- [pytilpack.importlib](pytilpack/importlib.py)
- [pytilpack.json](pytilpack/json.py)
- [pytilpack.logging](pytilpack/logging.py)
- [pytilpack.markdown](pytilpack/markdown.py)
- [pytilpack.msal](pytilpack/msal.py)
- [pytilpack.openai](pytilpack/openai.py)
- [pytilpack.pathlib](pytilpack/pathlib.py)
- [pytilpack.pycrypto](pytilpack/pycrypto.py)
- [pytilpack.pydantic](pytilpack/pydantic.py)
- [pytilpack.pytest](pytilpack/pytest.py)
- [pytilpack.python](pytilpack/python.py)
- [pytilpack.quart](pytilpack/quart/__init__.py)
- [pytilpack.quart_auth](pytilpack/quart_auth.py)
- [pytilpack.sqlalchemy](pytilpack/sqlalchemy/__init__.py)
- [pytilpack.threading](pytilpack/threading.py)
- [pytilpack.threadinga](pytilpack/threadinga.py): asyncio版
- [pytilpack.tiktoken](pytilpack/tiktoken.py)
- [pytilpack.tqdm](pytilpack/tqdm.py)
- [pytilpack.typing](pytilpack/typing.py)
- [pytilpack.yaml](pytilpack/yaml.py)

## 特定ライブラリに依存しないモジュール

- [pytilpack.cache](pytilpack/cache.py): ファイルキャッシュ関連
- [pytilpack.data_url](pytilpack/data_url.py): データURL関連
- [pytilpack.healthcheck](pytilpack/healthcheck.py): ヘルスチェック処理関連
- [pytilpack.htmlrag](pytilpack/htmlrag.py): HtmlRAG関連
- [pytilpack.http](pytilpack/http.py): HTTP関連
- [pytilpack.io](pytilpack/io.py): IO関連のユーティリティ
- [pytilpack.jsonc](pytilpack/jsonc.py): JSON with Comments関連
- [pytilpack.paginator](pytilpack/paginator.py): ページネーション関連
- [pytilpack.random](pytilpack/random.py): 疑似乱数関連
- [pytilpack.secrets](pytilpack/secrets.py): シークレットキー関連
- [pytilpack.sse](pytilpack/sse.py): Server-Sent Events関連
- [pytilpack.web](pytilpack/web.py): Web関連

## ドキュメント

- [ドキュメント一覧](docs/README.md)
- [CLIコマンド](docs/cli.md)
- [開発手順](docs/development.md)
