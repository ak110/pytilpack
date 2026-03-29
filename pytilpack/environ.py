"""環境変数ユーティリティ。"""

import decimal
import os
import pathlib
import typing

import dotenv

import pytilpack.python


class _Unset:
    """未指定を表すクラス。"""


_UNSET = _Unset()


def load_dotenv(path: str | pathlib.Path | None = None, override: bool = False) -> None:
    """python-dotenvを使用して.envファイルを読み込む。"""
    dotenv.load_dotenv(dotenv_path=path, override=override)


@typing.overload
def get_str(key: str) -> str: ...


@typing.overload
def get_str(key: str, default: str) -> str: ...


def get_str(key: str, default: str | _Unset = _UNSET) -> str:
    """環境変数を文字列として取得する。"""
    value = os.environ.get(key)
    if value is None:
        if isinstance(default, _Unset):
            raise ValueError(f"環境変数 {key} が設定されていません")
        return default
    return value


@typing.overload
def get_int(key: str) -> int: ...


@typing.overload
def get_int(key: str, default: int) -> int: ...


def get_int(key: str, default: int | _Unset = _UNSET) -> int:
    """環境変数を整数として取得する。"""
    value = os.environ.get(key)
    if value is None:
        if isinstance(default, _Unset):
            raise ValueError(f"環境変数 {key} が設定されていません")
        return default
    return pytilpack.python.convert(value, int, 0, errors="strict")


@typing.overload
def get_float(key: str) -> float: ...


@typing.overload
def get_float(key: str, default: float) -> float: ...


def get_float(key: str, default: float | _Unset = _UNSET) -> float:
    """環境変数を浮動小数点数として取得する。"""
    value = os.environ.get(key)
    if value is None:
        if isinstance(default, _Unset):
            raise ValueError(f"環境変数 {key} が設定されていません")
        return default
    return pytilpack.python.convert(value, float, 0.0, errors="strict")


@typing.overload
def get_bool(key: str) -> bool: ...


@typing.overload
def get_bool(key: str, default: bool) -> bool: ...


def get_bool(key: str, default: bool | _Unset = _UNSET) -> bool:
    """環境変数を真偽値として取得する。"""
    value = os.environ.get(key)
    if value is None:
        if isinstance(default, _Unset):
            raise ValueError(f"環境変数 {key} が設定されていません")
        return default
    return pytilpack.python.convert(value, bool, False, errors="strict")


@typing.overload
def get_decimal(key: str) -> decimal.Decimal: ...


@typing.overload
def get_decimal(key: str, default: decimal.Decimal) -> decimal.Decimal: ...


def get_decimal(key: str, default: decimal.Decimal | _Unset = _UNSET) -> decimal.Decimal:
    """環境変数をDecimalとして取得する。"""
    value = os.environ.get(key)
    if value is None:
        if isinstance(default, _Unset):
            raise ValueError(f"環境変数 {key} が設定されていません")
        return default
    try:
        return decimal.Decimal(value)
    except decimal.InvalidOperation as e:
        raise ValueError(f"環境変数 {key} の値 '{value}' をDecimalに変換できません") from e


@typing.overload
def get_path(key: str) -> pathlib.Path: ...


@typing.overload
def get_path(key: str, default: pathlib.Path) -> pathlib.Path: ...


def get_path(key: str, default: pathlib.Path | _Unset = _UNSET) -> pathlib.Path:
    """環境変数をPathとして取得する。"""
    value = os.environ.get(key)
    if value is None:
        if isinstance(default, _Unset):
            raise ValueError(f"環境変数 {key} が設定されていません")
        return default
    return pathlib.Path(value).resolve()


@typing.overload
def get_list(key: str, separator: str = ",") -> list[str]: ...


@typing.overload
def get_list(key: str, separator: str = ",", *, default: list[str]) -> list[str]: ...


def get_list(key: str, separator: str = ",", *, default: list[str] | _Unset = _UNSET) -> list[str]:
    """環境変数をリストとして取得する。

    セパレータで分割し、各要素の前後の空白を除去し、空文字列を除外する。
    """
    value = os.environ.get(key)
    if value is None:
        if isinstance(default, _Unset):
            raise ValueError(f"環境変数 {key} が設定されていません")
        return default
    return [s for s in (item.strip() for item in value.split(separator)) if s]


def get_or_none(key: str) -> str | None:
    """環境変数を取得する。未設定の場合はNoneを返す。"""
    return os.environ.get(key)
