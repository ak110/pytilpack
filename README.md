# pytilpack

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Lint&Test](https://github.com/ak110/pytilpack/actions/workflows/python-app.yml/badge.svg)](https://github.com/ak110/pytilpack/actions/workflows/python-app.yml)
[![PyPI version](https://badge.fury.io/py/pytilpack.svg)](https://badge.fury.io/py/pytilpack)

Pythonの各種ライブラリのユーティリティ集。

## インストール

```bash
pip install pytilpack
# pip install pytilpack[all]
# pip install pytilpack[flask]
# pip install pytilpack[flask-dev]  # pytest用
# pip install pytilpack[flask-login]
# pip install pytilpack[openai]
# pip install pytilpack[sqlalchemy]
# pip install pytilpack[tiktoken]
# pip install pytilpack[tqdm]
# pip install pytilpack[yaml]
```

## 使い方

```python
import pytilpack.xxx_
```

xxxのところは各種モジュール名。`openai`とか`pathlib`とか。
それぞれのモジュールに関連するユーティリティ関数などが入っている。

### モジュール一覧

- [pytilpack.csv_](pytilpack/csv_.py)
- [pytilpack.flask_](pytilpack/flask_.py)
- [pytilpack.flask_login_](pytilpack/flask_.py)
- [pytilpack.functools_](pytilpack/functools_.py)
- [pytilpack.json_](pytilpack/json_.py)
- [pytilpack.logging_](pytilpack/logging_.py)
- [pytilpack.openai_](pytilpack/openai_.py)
- [pytilpack.pathlib_](pytilpack/pathlib_.py)
- [pytilpack.python_](pytilpack/python_.py)
- [pytilpack.sqlalchemy_](pytilpack/sqlalchemy_.py)
- [pytilpack.tiktoken_](pytilpack/tiktoken_.py)
- [pytilpack.tqdm_](pytilpack/tqdm_.py)
- [pytilpack.yaml_](pytilpack/yaml_.py)
