# pytilpack

[![CI][ci-badge]][ci-link]

[ci-badge]: https://github.com/ak110/pytilpack/actions/workflows/ci.yaml/badge.svg
[ci-link]: https://github.com/ak110/pytilpack/actions/workflows/ci.yaml
[![PyPI version](https://badge.fury.io/py/pytilpack.svg)](https://badge.fury.io/py/pytilpack)

Pythonのユーティリティ集。

## 特徴

- モジュール単位の個別import: 必要なモジュールだけ取り込む
- extrasによる依存の最小化: 対象ライブラリごとに追加インストール
- CLI同梱: `pytilpack`コマンドで各種サブコマンドを提供
- 主要Pythonライブラリ向けユーティリティ（FastAPI / Flask / Quart / SQLAlchemy / Pydanticなど）

## インストール

ベースパッケージ（stdlib系ユーティリティ + beautifulsoup4/httpx/mcp/typing-extensions/werkzeug）:

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
uvx pytilpack mcp
uvx --from 'pytilpack[sqlalchemy]' pytilpack wait-for-db-connection "$SQLALCHEMY_DATABASE_URI"
```

### extras 一覧

| Extra | 対象モジュール | 主な依存パッケージ |
| ----- | -------------- | ------------------ |
| `all` | 全モジュール | (全依存) |
| `babel` | `.babel`, `.i18n` | babel |
| `bleach` | (markdown extraに含まれる) | bleach |
| `environ` | `.environ` | python-dotenv |
| `fastapi` | `.fastapi` | fastapi, html5lib |
| `flask` | `.flask`, `.flask_login` | flask, flask-login, html5lib |
| `markdown` | `.markdown` | bleach, markdown, tinycss2 |
| `msal` | `.msal` | azure-identity, cryptography, msal |
| `pycryptodome` | `.pycrypto` | pycryptodome |
| `pydantic` | `.pydantic` | pydantic |
| `pytest` | `.pytest` | pytest, pytest-asyncio |
| `pyyaml` | `.yaml` | pyyaml |
| `quart` | `.quart`, `.quart_auth` | quart, quart-auth, hypercorn, uvicorn |
| `sqlalchemy` | `.sqlalchemy` | sqlalchemy, tabulate |
| `tiktoken` | `.tiktoken` | tiktoken, openai, pillow |
| `tqdm` | `.tqdm` | tqdm |
| `web` | `.web` (check_html) | html5lib |

extras不要のモジュール（ベースパッケージに含まれる）の代表例は以下のとおり。
全モジュール一覧は[ドキュメント](https://ak110.github.io/pytilpack/)を参照。

- `.cache` / `.crypto` / `.data_url` / `.functools`
- `.healthcheck` / `.htmlrag` / `.http` / `.httpx` / `.io`
- `.json` / `.jsonc` / `.paginator` / `.random`
- `.ratelimit` / `.secrets` / `.sse` / `.validator`

## 主な使い方

各モジュールを個別にimportして利用する。

```python
import pytilpack.xxx
```

`xxx` には対象ライブラリ名（`httpx` や `pathlib` など）が入る。

モジュール一覧やAPIリファレンスは[ドキュメント](https://ak110.github.io/pytilpack/)を参照。
一部はCLIもある。詳細は[CLIコマンド](https://ak110.github.io/pytilpack/guide/cli/)を参照。

## ドキュメント

- <https://ak110.github.io/pytilpack/> — 概要・モジュール一覧・APIリファレンス
- <https://ak110.github.io/pytilpack/llms.txt> — LLM向け構造化インデックス
- [docs/development/development.md](docs/development/development.md) — 開発者向け情報
