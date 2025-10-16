# pytilpack

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Lint&Test](https://github.com/ak110/pytilpack/actions/workflows/test.yml/badge.svg)](https://github.com/ak110/pytilpack/actions/workflows/test.yml)
[![PyPI version](https://badge.fury.io/py/pytilpack.svg)](https://badge.fury.io/py/pytilpack)

Pythonのユーティリティ集。

## インストール

```bash
pip install pytilpack
# pip install pytilpack[all]
# pip install pytilpack[fastapi]
# pip install pytilpack[flask]
# pip install pytilpack[markdown]
# pip install pytilpack[openai]
# pip install pytilpack[pyyaml]
# pip install pytilpack[quart]
# pip install pytilpack[sqlalchemy]
# pip install pytilpack[tiktoken]
# pip install pytilpack[tqdm]
```

## 使い方

### import

各モジュールを個別にimportして利用する。

```python
import pytilpack.xxx
```

xxxのところは対象ライブラリと同名になっている。`openai`とか`pathlib`とか。
それぞれのモジュールに関連するユーティリティ関数などが入っている。

特定のライブラリに依存しないものもある。

### モジュール一覧

### 各種ライブラリ用のユーティリティのモジュール一覧

- [pytilpack.asyncio](pytilpack/asyncio.py)
- [pytilpack.base64](pytilpack/base64.py)
- [pytilpack.csv](pytilpack/csv.py)
- [pytilpack.dataclasses](pytilpack/dataclasses.py)
- [pytilpack.datetime](pytilpack/datetime.py)
- [pytilpack.fastapi](pytilpack/fastapi_/__init_.py)
- [pytilpack.flask](pytilpack/flask_/__init_.py)
- [pytilpack.flask_login](pytilpack/flask.py)
- [pytilpack.fnctl](pytilpack/fnctl.py)
- [pytilpack.functools](pytilpack/functools.py)
- [pytilpack.httpx](pytilpack/httpx.py)
- [pytilpack.importlib](pytilpack/importlib.py)
- [pytilpack.json](pytilpack/json.py)
- [pytilpack.logging](pytilpack/logging.py)
- [pytilpack.openai](pytilpack/openai.py)
- [pytilpack.pathlib](pytilpack/pathlib.py)
- [pytilpack.pycrypto](pytilpack/pycrypto.py)
- [pytilpack.python](pytilpack/python.py)
- [pytilpack.quart](pytilpack/quart_/__init_.py)
- [pytilpack.sqlalchemy](pytilpack/sqlalchemy.py)
- [pytilpack.sqlalchemya](pytilpack/sqlalchemya.py)  # asyncio版
- [pytilpack.threading](pytilpack/threading.py)
- [pytilpack.threadinga](pytilpack/threadinga.py)  # asyncio版
- [pytilpack.tiktoken](pytilpack/tiktoken.py)
- [pytilpack.tqdm](pytilpack/tqdm.py)
- [pytilpack.typing](pytilpack/typing.py)
- [pytilpack.yaml](pytilpack/yaml.py)

### 特定のライブラリに依存しないモジュール一覧

- [pytilpack.cache](pytilpack/cache.py)  # ファイルキャッシュ関連
- [pytilpack.data_url](pytilpack/data_url.py)  # データURL関連
- [pytilpack.healthcheck](pytilpack/healthcheck.py)  # ヘルスチェック処理関連
- [pytilpack.htmlrag](pytilpack/htmlrag.py)  # HtmlRAG関連
- [pytilpack.http](pytilpack/http.py)  # HTTP関連
- [pytilpack.sse](pytilpack/sse.py)  # Server-Sent Events関連
- [pytilpack.web](pytilpack/web.py)  # Web関連

## CLIコマンド

一部の機能はCLIコマンドとしても利用可能。

### 空のディレクトリを削除

```bash
pytilpack delete_empty_dirs path/to/dir [--no-keep-root] [--verbose]
```

- 空のディレクトリを削除
- デフォルトでルートディレクトリを保持（`--no-keep-root`で削除可能）

### 古いファイルを削除

```bash
pytilpack delete_old_files path/to/dir --days=7 [--no-delete-empty-dirs] [--no-keep-root-empty-dir] [--verbose]
```

- 指定した日数より古いファイルを削除（`--days`オプションで指定）
- デフォルトで空ディレクトリを削除（`--no-delete-empty-dirs`で無効化）
- デフォルトでルートディレクトリを保持（`--no-keep-root-empty-dir`で削除可能）

### ディレクトリを同期

```bash
pytilpack sync src dst [--delete] [--verbose]
```

- コピー元(src)からコピー先(dst)へファイル・ディレクトリを同期
- 日付が異なるファイルをコピー
- `--delete`オプションでコピー元に存在しないコピー先のファイル・ディレクトリを削除

### URLの内容を取得

```bash
pytilpack fetch url [--no-verify] [--verbose]
```

- URLからHTMLを取得し、簡略化して標準出力に出力
- `--no-verify`オプションでSSL証明書の検証を無効化
- `--verbose`オプションで詳細なログを出力

### MCPサーバーを起動

```bash
pytilpack mcp [--transport=stdio] [--host=localhost] [--port=8000] [--verbose]
```

- Model Context ProtocolサーバーとしてpytilpackのFetch機能を提供
- `--transport`オプションで通信方式を指定（stdio/http、デフォルト: stdio）
- `--host`オプションでサーバーのホスト名を指定（httpの場合のみ使用、デフォルト: localhost）
- `--port`オプションでサーバーのポート番号を指定（httpの場合のみ使用、デフォルト: 8000）
- `--verbose`オプションで詳細なログを出力

#### stdioモード

```bash
pytilpack mcp
# または
pytilpack mcp --transport=stdio
```

#### httpモード

```bash
pytilpack mcp --transport=http --port=8000
```

## 開発手順

- [DEVELOPMENT.md](DEVELOPMENT.md) を参照
