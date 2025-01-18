# カスタム指示

- importは可能な限り`import xxx`形式で書く (`from xxx import yyy`ではなく)
- タイプヒントは可能な限り書く
- docstringは基本的には概要のみ書く
- ログは`logging`を使う
- 日付関連の処理は`datetime`を使う
- ファイル関連の処理は`pathlib`を使う
- テーブルデータの処理には`polars`を使う (`pandas`は使わない)
- テストコードは`pytest`で書く
  - テストコードは`pytilpack/xxx_.py`に対して`tests/xxx_test.py`として配置する
