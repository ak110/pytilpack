"""pydantic関連。"""

import sys
import traceback
import types

import pydantic


def format_exc() -> str:
    """現在の例外がPydanticのバリデーションエラーである場合、そのエラーを整形して返す。"""
    return format_exception(*sys.exc_info())


def format_exception(exc: type[BaseException] | None, value: BaseException | None, tb: types.TracebackType | None) -> str:
    """例外がPydanticのバリデーションエラーである場合、そのエラーを整形して返す。"""
    if isinstance(value, pydantic.ValidationError):
        return format_error(value)
    # 違う場合は仕方ないので標準ライブラリへ
    return "\n".join(traceback.format_exception(exc, value, tb))


def format_error(e: pydantic.ValidationError, title: str | None = None) -> str:
    """Pydanticのバリデーションエラーを整形して返す。

    Args:
        e: Pydanticのバリデーションエラー
        title: タイトル。Noneの場合はe.titleを使う。

    """
    errors = []
    for error in e.errors():
        loc = ".".join(map(str, error["loc"]))
        if loc == "":
            # @pydantic.model_validatorを使った場合
            msg = error["msg"].removeprefix("Value error, ")
            errors.append(f"  {msg} (type={error['type']})")
        else:
            # 単一フィールドのエラー
            details = {"type": error["type"], "input": error.get("input")}
            details_str = ", ".join(f"{k}={v}" for k, v in details.items() if v is not None)
            errors.append(f"  {loc}: {error['msg']} ({details_str})")
    if title is None:
        title = e.title
    return f"{title}\n" + "\n".join(errors)
