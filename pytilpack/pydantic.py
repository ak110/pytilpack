__lazy_modules__ = ["pydantic", "sys", "traceback", "types"]

import sys
import traceback
import types

import pydantic


def format_exc() -> str:
    return format_exception(*sys.exc_info())


def format_exception(exc: type[BaseException] | None, value: BaseException | None, tb: types.TracebackType | None) -> str:
    if isinstance(value, pydantic.ValidationError):
        return format_error(value)
    return "\n".join(traceback.format_exception(exc, value, tb))


def format_error(e: pydantic.ValidationError, title: str | None = None) -> str:
    errors = []
    for error in e.errors():
        loc = ".".join(map(str, error["loc"]))
        if loc == "":
            msg = error["msg"].removeprefix("Value error, ")
            errors.append(f"  {msg} (type={error['type']})")
        else:
            details = {"type": error["type"], "input": error.get("input")}
            details_str = ", ".join(f"{k}={v}" for k, v in details.items() if v is not None)
            errors.append(f"  {loc}: {error['msg']} ({details_str})")
    if title is None:
        title = e.title
    return f"{title}\n" + "\n".join(errors)
