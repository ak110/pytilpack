"""環境変数ユーティリティ。"""

import collections.abc
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
def get_str(key: str, *, environ: collections.abc.Mapping[str, str] | None = None) -> str: ...


@typing.overload
def get_str(key: str, default: str, *, environ: collections.abc.Mapping[str, str] | None = None) -> str: ...


def get_str(
    key: str,
    default: str | _Unset = _UNSET,
    *,
    environ: collections.abc.Mapping[str, str] | None = None,
) -> str:
    """環境変数を文字列として取得する。"""
    value = (os.environ if environ is None else environ).get(key)
    if value is None:
        if isinstance(default, _Unset):
            raise ValueError(f"環境変数 {key} が設定されていません")
        return default
    return value


@typing.overload
def get_int(key: str, *, environ: collections.abc.Mapping[str, str] | None = None) -> int: ...


@typing.overload
def get_int(key: str, default: int, *, environ: collections.abc.Mapping[str, str] | None = None) -> int: ...


def get_int(
    key: str,
    default: int | _Unset = _UNSET,
    *,
    environ: collections.abc.Mapping[str, str] | None = None,
) -> int:
    """環境変数を整数として取得する。"""
    value = (os.environ if environ is None else environ).get(key)
    if value is None:
        if isinstance(default, _Unset):
            raise ValueError(f"環境変数 {key} が設定されていません")
        return default
    return pytilpack.python.convert(value, int, 0, errors="strict")


@typing.overload
def get_float(key: str, *, environ: collections.abc.Mapping[str, str] | None = None) -> float: ...


@typing.overload
def get_float(
    key: str,
    default: float,
    *,
    environ: collections.abc.Mapping[str, str] | None = None,
) -> float: ...


def get_float(
    key: str,
    default: float | _Unset = _UNSET,
    *,
    environ: collections.abc.Mapping[str, str] | None = None,
) -> float:
    """環境変数を浮動小数点数として取得する。"""
    value = (os.environ if environ is None else environ).get(key)
    if value is None:
        if isinstance(default, _Unset):
            raise ValueError(f"環境変数 {key} が設定されていません")
        return default
    return pytilpack.python.convert(value, float, 0.0, errors="strict")


@typing.overload
def get_bool(key: str, *, environ: collections.abc.Mapping[str, str] | None = None) -> bool: ...


@typing.overload
def get_bool(
    key: str,
    default: bool,
    *,
    environ: collections.abc.Mapping[str, str] | None = None,
) -> bool: ...


def get_bool(
    key: str,
    default: bool | _Unset = _UNSET,
    *,
    environ: collections.abc.Mapping[str, str] | None = None,
) -> bool:
    """環境変数を真偽値として取得する。"""
    value = (os.environ if environ is None else environ).get(key)
    if value is None:
        if isinstance(default, _Unset):
            raise ValueError(f"環境変数 {key} が設定されていません")
        return default
    return pytilpack.python.convert(value, bool, False, errors="strict")


@typing.overload
def get_decimal(key: str, *, environ: collections.abc.Mapping[str, str] | None = None) -> decimal.Decimal: ...


@typing.overload
def get_decimal(
    key: str,
    default: decimal.Decimal,
    *,
    environ: collections.abc.Mapping[str, str] | None = None,
) -> decimal.Decimal: ...


def get_decimal(
    key: str,
    default: decimal.Decimal | _Unset = _UNSET,
    *,
    environ: collections.abc.Mapping[str, str] | None = None,
) -> decimal.Decimal:
    """環境変数をDecimalとして取得する。"""
    value = (os.environ if environ is None else environ).get(key)
    if value is None:
        if isinstance(default, _Unset):
            raise ValueError(f"環境変数 {key} が設定されていません")
        return default
    try:
        return decimal.Decimal(value)
    except decimal.InvalidOperation as e:
        raise ValueError(f"環境変数 {key} の値 '{value}' をDecimalに変換できません") from e


@typing.overload
def get_path(key: str, *, environ: collections.abc.Mapping[str, str] | None = None) -> pathlib.Path: ...


@typing.overload
def get_path(
    key: str,
    default: pathlib.Path,
    *,
    environ: collections.abc.Mapping[str, str] | None = None,
) -> pathlib.Path: ...


def get_path(
    key: str,
    default: pathlib.Path | _Unset = _UNSET,
    *,
    environ: collections.abc.Mapping[str, str] | None = None,
) -> pathlib.Path:
    """環境変数をPathとして取得する。"""
    value = (os.environ if environ is None else environ).get(key)
    if value is None:
        if isinstance(default, _Unset):
            raise ValueError(f"環境変数 {key} が設定されていません")
        return default
    return pathlib.Path(value).resolve()


@typing.overload
def get_list(
    key: str,
    separator: str = ",",
    *,
    environ: collections.abc.Mapping[str, str] | None = None,
) -> list[str]: ...


@typing.overload
def get_list(
    key: str,
    separator: str = ",",
    *,
    default: list[str],
    environ: collections.abc.Mapping[str, str] | None = None,
) -> list[str]: ...


def get_list(
    key: str,
    separator: str = ",",
    *,
    default: list[str] | _Unset = _UNSET,
    environ: collections.abc.Mapping[str, str] | None = None,
) -> list[str]:
    """環境変数をリストとして取得する。

    セパレータで分割し、各要素の前後の空白を除去し、空文字列を除外する。
    """
    value = (os.environ if environ is None else environ).get(key)
    if value is None:
        if isinstance(default, _Unset):
            raise ValueError(f"環境変数 {key} が設定されていません")
        return default
    return [s for s in (item.strip() for item in value.split(separator)) if s]


def get_or_none(key: str, *, environ: collections.abc.Mapping[str, str] | None = None) -> str | None:
    """環境変数を取得する。未設定の場合はNoneを返す。"""
    return (os.environ if environ is None else environ).get(key)
