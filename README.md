# pytilpack

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Lint&Test](https://github.com/ak110/pytilpack/actions/workflows/python-app.yml/badge.svg)](https://github.com/ak110/pytilpack/actions/workflows/python-app.yml)
[![PyPI version](https://badge.fury.io/py/pytilpack.svg)](https://badge.fury.io/py/pytilpack)

Pythonの各種ライブラリのユーティリティ集。

## インストール

```bash
pip install pytilpack
# pip install pytilpack[all]
# pip install pytilpack[fastapi]
# pip install pytilpack[flask]
# pip install pytilpack[htmlrag]
# pip install pytilpack[markdown]
# pip install pytilpack[openai]
# pip install pytilpack[pyyaml]
# pip install pytilpack[quart]
# pip install pytilpack[sqlalchemy]
# pip install pytilpack[tiktoken]
# pip install pytilpack[tqdm]
```

## 使い方

### 各種ライブラリ用のユーティリティ

```python
import pytilpack.xxx_
```

xxxのところは各種モジュール名。`openai`とか`pathlib`とか。
それぞれのモジュールに関連するユーティリティ関数などが入っている。

### その他のユーティリティ

```python
import pytilpack.xxx
```

特定のライブラリに依存しないユーティリティ関数などが入っている。

### モジュール一覧

### 各種ライブラリ用のユーティリティのモジュール一覧

- [pytilpack.asyncio_](pytilpack/asyncio_.py)
- [pytilpack.base64_](pytilpack/base64_.py)
- [pytilpack.csv_](pytilpack/csv_.py)
- [pytilpack.dataclasses_](pytilpack/dataclasses_.py)
- [pytilpack.fastapi_](pytilpack/fastapi_.py)
- [pytilpack.flask_](pytilpack/flask_.py)
- [pytilpack.flask_login_](pytilpack/flask_.py)
- [pytilpack.functools_](pytilpack/functools_.py)
- [pytilpack.json_](pytilpack/json_.py)
- [pytilpack.logging_](pytilpack/logging_.py)
- [pytilpack.openai_](pytilpack/openai_.py)
- [pytilpack.pathlib_](pytilpack/pathlib_.py)
- [pytilpack.python_](pytilpack/python_.py)
- [pytilpack.quart_](pytilpack/quart_.py)
- [pytilpack.sqlalchemy_](pytilpack/sqlalchemy_.py)
- [pytilpack.threading_](pytilpack/threading_.py)
- [pytilpack.tiktoken_](pytilpack/tiktoken_.py)
- [pytilpack.tqdm_](pytilpack/tqdm_.py)
- [pytilpack.yaml_](pytilpack/yaml_.py)

### その他のユーティリティのモジュール一覧

- [pytilpack.cache](pytilpack/cache.py)  # ファイルキャッシュ関連
- [pytilpack.data_url](pytilpack/data_url.py)  # データURL関連
- [pytilpack.htmlrag](pytilpack/htmlrag.py)  # HtmlRAG関連
- [pytilpack.sse](pytilpack/sse.py)  # Server-Sent Events関連
- [pytilpack.web](pytilpack/web.py)  # Web関連

## 開発手順

- [DEVELOPMENT.md](DEVELOPMENT.md) を参照
