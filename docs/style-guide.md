# スタイルガイド

## 全般

- 関数やクラスなどの定義の順番は可能な限りトップダウンにする。
  つまり関数Aから関数Bを呼び出す場合、関数Aを前に、関数Bを後ろに定義する。
  (呼び出す側が上、呼び出される側が下)

## Python

- importについて
  - 可能な限り`import xxx`形式で書く (`from xxx import yyy`ではなく)
  - 可能な限りトップレベルでimportする (循環参照や初期化順による問題を避ける場合に限りブロック内も可)
- タイプヒントは可能な限り書く
  - `typing.List`ではなく`list`を使用する。`dict`やその他も同様。
  - `typing.Optional`ではなく`| None`を使用する。
- docstringは基本的には概要のみ書く
- ログは`logging`を使う
- 日付関連の処理は`datetime`を使う
- ファイル関連の処理は`pathlib`を使う (`open`関数や`os`モジュールは使わない)
- テーブルデータの処理には`polars`を使う (`pandas`は使わない)
- パッケージ管理には`uv`を使う
- .venvの更新には`make update`を使う
- コードを書いた後は必ず`make format`で整形する
  - 新しいファイルを作成する場合は近い階層の代表的なファイルを確認し、可能な限りスタイルを揃える
- `make test`でmypy, pytestなどをまとめて実行できる
- インターフェースの都合上未使用の引数がある場合は、関数先頭で`del xxx # noqa`のように書く(lint対策)
- 単なる長い名前の別名でしかないローカル変数は作らない。例えば `x = cls.foo` と書いて `x` を使うより `cls.foo` を直接使う。

### Pythonテストコード

- テストコードは`pytest`で書く
- テストコードは`pytilpack/xxx.py`に対して`tests/xxx_test.py`として配置する
  - `pytilpack/xxx/yyy.py`に対して`tests/xxx/yyy_test.py`
  - `xxx`がpythonキーワードなどの場合、`xxx_.py`になる。そのときは`xxx_test.py`とする (アンダースコアは無視)
- テストコードは速度と簡潔さを重視する。
  - テスト関数を細かく分け過ぎず、一連の流れをまとめて1つの関数にする。
    - 例えば、saveとloadならまとめてtest_save_loadのようにする。(こういう関係ある関数以外はまとめず別々に。)
  - 網羅性のため、必要に応じて `pytest.mark.parametrize` を使用する。
  - sleepなどは0.01秒単位とし、テスト関数全体で0.1秒を超えないようにする。

テストコードの例。

```python
"""テストコード。"""

import pathlib

import pytest
import pytilpack.xxx_


@pytest.mark.parametrize(
    "x,expected",
    [
        ("test1", "test1"),
        ("test2", "test2"),
    ],
)
def test_yyy(tmp_path: pathlib.Path, x: str, expected: str) -> None:
    """yyyのテスト。"""
    actual = pytilpack.xxx_.yyy(tmp_path, x)
    assert actual == expected
```

- テストコードの実行は `uv run pyfltr <path>` を使う (pytestを直接呼び出さない)
  - `-vv`などが必要な場合に限り `uv run pyfltr -vv <path>` のようにする

## Markdown記述スタイル

- `**`は強調したい箇所のみに使い、箇条書きの見出し用途では使わない
  - NG例: `1. **xx機能**: xxをyyする`
- できるだけmarkdownlintが通るように書く
  - 特に注意するルール:
    - `MD040/fenced-code-language`: Fenced code blocks should have a language specified
- 図はMermaid記法で書く
- 別のMarkdownファイルへのリンクは、基本的に`[プロジェクトルートからのパス](記述個所からの相対パス)`で書く
- lintの実行方法: `uv run pre-commit run --files <file>`
