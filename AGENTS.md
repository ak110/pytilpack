# カスタム指示

- プロジェクト概要: @README.md
- リリース手順など: @DEVELOPMENT.md
- モジュール追加時は`README.md`の更新要

## 原則

- 以下を念頭に置いて実装を進めること
  - DRY: **Don't Repeat Yourself**
  - KISS: **Keep It Simple, Stupid**
  - SSOT: **Single Source Of Truth**
  - SRP: **Single Responsibility Principle**
  - コードには How、
    テストコードには What、
    コミットログには Why、
    コードコメントには Why not を書く。
- `git grep`コマンドを活用して影響範囲やコードスタイルを調査する

## コーディングスタイル全般

- 関数やクラスなどの定義の順番は可能な限りトップダウンにする。
  つまり関数Aから関数Bを呼び出す場合、関数Aを前に、関数Bを後ろに定義する。

## Pythonコーディングスタイル

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
  ― 新しいファイルを作成する場合は近い階層の代表的なファイルを確認し、スタイルを揃える
― 新しいファイルを作成する場合は近い階層の代表的なファイルを確認し、可能な限りスタイルを揃える
- `make test`でmypy, pytestなどをまとめて実行できる
- インターフェースの都合上未使用の引数がある場合は、関数先頭で`del xxx # noqa`のように書く(lint対策)

### Pythonテストコード

- テストコードは`pytest`で書く
- テストコードは`pytilpack/xxx_.py`に対して`tests/xxx_test.py`として配置する
- テストコードは速度と簡潔さを重視する。
  - テスト関数を細かく分けず、一連の流れをまとめて1つの関数にする。
  - 網羅性のため、必要に応じて `pytest.mark.parametrize` を使用する。
  - sleepなどは0.01秒単位とし、テスト関数全体で0.1秒を超えないようにする。

テストコードの例:

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

- テストコードの実行は `uv run pytest`
