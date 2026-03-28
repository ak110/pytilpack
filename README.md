# pytilpack

[![CI](https://github.com/ak110/pytilpack/actions/workflows/ci.yaml/badge.svg)](https://github.com/ak110/pytilpack/actions/workflows/ci.yaml)
[![PyPI version](https://badge.fury.io/py/pytilpack.svg)](https://badge.fury.io/py/pytilpack)

Pythonのユーティリティ集。

- [ドキュメント](https://ak110.github.io/pytilpack/)
- [llms.txt](https://ak110.github.io/pytilpack/llms.txt)

## インストール

```bash
pip install pytilpack
# pip install pytilpack[all]
# pip install pytilpack[anthropic]
# pip install pytilpack[dotenv]
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

モジュール一覧やAPIリファレンスは[ドキュメント](https://ak110.github.io/pytilpack/)を参照。
一部は CLI もある。詳細は[CLIコマンド](https://ak110.github.io/pytilpack/cli/)を参照。
