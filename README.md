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
- [pytilpack.fastapi_](pytilpack/fastapi_/__init__.py)
- [pytilpack.flask_](pytilpack/flask_/__init__.py)
- [pytilpack.flask_login_](pytilpack/flask_.py)
- [pytilpack.functools_](pytilpack/functools_.py)
- [pytilpack.json_](pytilpack/json_.py)
- [pytilpack.logging_](pytilpack/logging_.py)
- [pytilpack.openai_](pytilpack/openai_.py)
- [pytilpack.pathlib_](pytilpack/pathlib_.py)
- [pytilpack.python_](pytilpack/python_.py)
- [pytilpack.quart_](pytilpack/quart_/__init__.py)
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

## CLIコマンド

一部の機能はCLIコマンドとしても利用可能。

### 空のディレクトリを削除

```bash
python -m pytilpack.cli.delete_empty_dirs path/to/dir [--no-keep-root] [--verbose]
```

- 空のディレクトリを削除
- デフォルトでルートディレクトリを保持（`--no-keep-root`で削除可能）

### 古いファイルを削除

```bash
python -m pytilpack.cli.delete_old_files path/to/dir --days=7 [--no-delete-empty-dirs] [--no-keep-root-empty-dir] [--verbose]
```

- 指定した日数より古いファイルを削除（`--days`オプションで指定）
- デフォルトで空ディレクトリを削除（`--no-delete-empty-dirs`で無効化）
- デフォルトでルートディレクトリを保持（`--no-keep-root-empty-dir`で削除可能）

### ディレクトリを同期

```bash
python -m pytilpack.cli.sync src dst [--delete] [--verbose]
```

- コピー元(src)からコピー先(dst)へファイル・ディレクトリを同期
- 日付が異なるファイルをコピー
- `--delete`オプションでコピー元に存在しないコピー先のファイル・ディレクトリを削除

## 開発手順

- [DEVELOPMENT.md](DEVELOPMENT.md) を参照
