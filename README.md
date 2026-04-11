# pytilpack

[![CI](https://github.com/ak110/pytilpack/actions/workflows/ci.yaml/badge.svg)](https://github.com/ak110/pytilpack/actions/workflows/ci.yaml)
[![PyPI version](https://badge.fury.io/py/pytilpack.svg)](https://badge.fury.io/py/pytilpack)

Pythonのユーティリティ集。

## 特徴

- モジュール単位の個別import: 必要なモジュールだけ取り込む
- extrasによる依存の最小化: 対象ライブラリごとに追加インストール
- CLI同梱: `pytilpack`コマンドで各種サブコマンドを提供
- 主要Pythonライブラリ向けユーティリティ（FastAPI / Flask / Quart / SQLAlchemy / Pydanticなど）

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
uvx pytilpack mcp
uvx --from 'pytilpack[sqlalchemy]' pytilpack wait-for-db-connection "$SQLALCHEMY_DATABASE_URI"
```

### extras 一覧

| Extra | 対象モジュール | 依存パッケージ |
| ----- | -------------- | -------------- |
| `all` | 全モジュール | (全依存) |
| `babel` | `.babel` `.i18n` | babel |
| `environ` | `.environ` | python-dotenv |
| `fastapi` | `.fastapi` | fastapi等 |
| `flask` | `.flask` `.flask_login` | flask等 |
| `markdown` | `.markdown` | bleach等 |
| `msal` | `.msal` | msal等 |
| `pycryptodome` | `.pycrypto` | pycryptodome |
| `pydantic` | `.pydantic` | pydantic |
| `pytest` | `.pytest` | pytest等 |
| `pyyaml` | `.yaml` | pyyaml |
| `quart` | `.quart` `.quart_auth` | quart等 |
| `sqlalchemy` | `.sqlalchemy` | sqlalchemy等 |
| `tiktoken` | `.tiktoken` | tiktoken等 |
| `tqdm` | `.tqdm` | tqdm |
| `web` | `.web` (check_html) | html5lib |

extras不要のモジュール（ベースパッケージに含まれる）は以下のとおり。

- `.cache` / `.crypto` / `.data_url` / `.functools`
- `.healthcheck` / `.http` / `.httpx` / `.io`
- `.json` / `.jsonc` / `.paginator` / `.random`
- `.ratelimit` / `.secrets` / `.sse` / `.validator` など

## 主な使い方

各モジュールを個別にimportして利用する。

```python
import pytilpack.xxx
```

`xxx` には対象ライブラリ名（`openai` や `pathlib` など）が入る。

モジュール一覧やAPIリファレンスは[ドキュメント](https://ak110.github.io/pytilpack/)を参照。
一部はCLIもある。詳細は[CLIコマンド](https://ak110.github.io/pytilpack/cli/)を参照。

## ドキュメント

- <https://ak110.github.io/pytilpack/> — 概要・モジュール一覧・APIリファレンス
- [llms.txt](https://ak110.github.io/pytilpack/llms.txt) — LLM向け構造化インデックス
- [docs/development/development.md](docs/development/development.md) — 開発者向け情報
