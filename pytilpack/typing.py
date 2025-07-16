"""typing関連のユーティリティ。"""

import dataclasses
import types
import typing


def get_literal_values(literal_type: typing.Any) -> list:
    """Literalの値を取得する。

    XXType: typing.TypeAlias = typing.Literal[1, 2, 3] のような型アノテーションなら
    typing.get_args(XXType) で値を取得できるが、
    type XXType = typing.Literal[1, 2, 3] のような型エイリアス(TypeAliasType?)の場合は
    XXType.__value__ に対して typing.get_args() を使う必要があるらしい…。
    <https://github.com/python/cpython/issues/112472>

    ZZType = XXType | ZZType やさらにその型エイリアスなどもいい感じに解決する。
    ここは判定方法よくわからないのでtyping.get_argsで出てこなくなるまで再帰する形に…。

    """
    # 型エイリアスの解決
    if isinstance(literal_type, typing.TypeAliasType):
        return get_literal_values(literal_type.__value__)

    # 再帰的にtyping.get_args()する
    args = list(typing.get_args(literal_type))
    if len(args) == 0:
        return [literal_type]
    return [sub_arg for arg in args for sub_arg in get_literal_values(arg)]


def is_instance_safe(value: typing.Any, expected_type: typing.Any, path: str = "") -> bool:
    """型チェックを行い、エラーの場合はFalseを返す。

    Args:
        value: 実際の値。
        expected_type: アノテーションで指定された型。
        path: エラー位置を示すパス（xxx.yyy形式）。

    Returns:
        bool: 型が一致すればTrue、合致しなければFalse。
    """
    try:
        return is_instance(value, expected_type, path)
    except TypeError:
        return False


def is_instance(value: typing.Any, expected_type: typing.Any, path: str = "") -> bool:
    """Recursively check whether *value* conforms to *expected_type*.

    Args:
        value: 実際の値。
        expected_type: アノテーションで指定された型。
        path: エラー位置を示すパス（xxx.yyy形式）。

    Returns:
        bool: 型が一致すればTrue、合致しなければFalse。

    Raises:
        TypeError: 型が一致しない場合、詳細なエラー位置を含む。
    """

    # NewType の場合、__supertype__ を確認
    if hasattr(expected_type, "__supertype__"):
        return is_instance(value, expected_type.__supertype__, path)
    # TypeAliasType の場合、__value__ を確認
    if isinstance(expected_type, typing.TypeAliasType):
        return is_instance(value, expected_type.__value__, path)

    origin = typing.get_origin(expected_type)

    # 組み込み型やユーザー定義クラス
    if origin is None:
        # typing.Anyの場合は常にTrue
        if expected_type is typing.Any:
            return True
        # dataclassの場合は再帰的にチェック
        if dataclasses.is_dataclass(expected_type):
            if not isinstance(value, expected_type):  # type: ignore[arg-type]
                _raise_type_error(value, expected_type, path)
            # dataclassのフィールドを再帰的にチェック
            hints = typing.get_type_hints(expected_type)
            for field in dataclasses.fields(expected_type):
                field_value = getattr(value, field.name)
                field_type = hints.get(field.name, typing.Any)
                field_path = f"{path}.{field.name}" if path else field.name
                if not is_instance(field_value, field_type, field_path):
                    return False
            return True
        else:
            if not isinstance(value, expected_type):
                _raise_type_error(value, expected_type, path)
            return True

    args = typing.get_args(expected_type)

    # Optional[X] / Union[X, Y, ...]
    if origin is typing.Union or origin is types.UnionType:
        for arg in args:
            try:
                if is_instance(value, arg, path):
                    return True
            except TypeError:
                continue
        _raise_type_error(value, expected_type, path)
        return False

    # list[X], set[X], tuple[X, ...]
    if origin in {list, set, tuple}:
        if not isinstance(value, origin):
            _raise_type_error(value, expected_type, path)
        if not args:  # list[Any] のように引数が無い場合
            return True
        elem_type = args[0]
        for i, elem in enumerate(value):
            elem_path = f"{path}[{i}]" if path else f"[{i}]"
            if not is_instance(elem, elem_type, elem_path):
                return False
        return True

    # dict[K, V]
    if origin is dict:
        if not isinstance(value, dict):
            _raise_type_error(value, expected_type, path)
        key_type, val_type = args
        for k, v in value.items():
            key_path = f"{path}[{k!r}]" if path else f"[{k!r}]"
            if not is_instance(k, key_type, f"{path}.<key>" if path else "<key>"):
                return False
            if not is_instance(v, val_type, key_path):
                return False
        return True

    # Literal[values...]
    if origin is typing.Literal:
        if value not in args:
            _raise_type_error(value, expected_type, path)
        return True

    # それ以外 (例: TypedDict, NewType 等) は簡易的にoriginで判定
    if not isinstance(value, origin):
        _raise_type_error(value, expected_type, path)
    return True


def _raise_type_error(value: typing.Any, expected_type: typing.Any, path: str) -> None:
    """型エラーを発生させる。

    Args:
        value: 実際の値。
        expected_type: 期待される型。
        path: エラー位置を示すパス。

    Raises:
        TypeError: 詳細なエラー情報を含む型エラー。
    """
    location = f"位置 {path}: " if path else ""
    raise TypeError(f"{location}型 {expected_type} を期待しますが、{type(value)} の値が設定されています。(値:{value!r})")
