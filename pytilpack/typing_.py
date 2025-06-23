"""typing関連のユーティリティ。"""

import types
import typing


def is_instance(value: typing.Any, expected_type: typing.Any) -> bool:
    """Recursively check whether *value* conforms to *expected_type*.

    Args:
        value: 実際の値。
        expected_type: アノテーションで指定された型。

    Returns:
        bool: 型が一致すればTrue、合致しなければFalse。
    """

    # NewType の場合は、__supertype__ を確認
    if hasattr(expected_type, "__supertype__"):
        return is_instance(value, expected_type.__supertype__)

    origin = typing.get_origin(expected_type)

    # 組み込み型やユーザー定義クラス
    if origin is None:
        return isinstance(value, expected_type)

    args = typing.get_args(expected_type)

    # Optional[X] / Union[X, Y, ...]
    if origin is typing.Union or origin is types.UnionType:
        return any(is_instance(value, arg) for arg in args)

    # list[X], set[X], tuple[X, ...]
    if origin in {list, set, tuple}:
        if not isinstance(value, origin):
            return False
        if not args:  # list[Any] のように引数が無い場合
            return True
        elem_type = args[0]
        return all(is_instance(elem, elem_type) for elem in value)

    # dict[K, V]
    if origin is dict:
        if not isinstance(value, dict):
            return False
        key_type, val_type = args
        return all(
            is_instance(k, key_type) and is_instance(v, val_type)
            for k, v in value.items()
        )

    # Literal[values...]
    if origin is typing.Literal:
        return value in args

    # それ以外 (例: TypedDict, NewType 等) は簡易的にoriginで判定
    return isinstance(value, origin)
