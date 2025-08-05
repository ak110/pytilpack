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


def format_error(e: pydantic.ValidationError) -> str:
    """Pydanticのバリデーションエラーを整形して返す。"""
    errors = []
    for error in e.errors():
        loc = ".".join(map(str, error["loc"]))
        details = {"type": error["type"], "input": error.get("input")}
        if "ctx" in error:
            details.update({"ctx": error["ctx"]})
        details_str = ", ".join(f"{k}={v}" for k, v in details.items() if v is not None)
        errors.append(f"  {loc}: {error['msg']} ({details_str})")
    return f"{e.title}\n" + "\n".join(errors)
