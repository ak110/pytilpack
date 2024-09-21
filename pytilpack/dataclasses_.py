"""dataclasses関連のユーティリティ。"""

import dataclasses


def asdict(obj):
    """dataclasses.asdict()のシャローコピーバージョン。

    dataclasses.asdict()はネストされたdataclassを再帰的に処理してしまうが、
    その挙動が要らない場合に使う。
    公式マニュアルに書いてある回避策そのままのコード。
    <https://docs.python.org/ja/3/library/dataclasses.html#dataclasses.asdict>

    """
    return {field.name: getattr(obj, field.name) for field in dataclasses.fields(obj)}
