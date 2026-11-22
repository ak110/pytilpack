__lazy_modules__ = [
    "contextlib",
    "contextvars",
    "datetime",
    "hashlib",
    "io",
    "json",
    "logging",
    "logging.handlers",
    "pathlib",
    "pytilpack.python",
    "re",
    "time",
    "typing",
    "uuid",
]

# pylint: disable=redefined-builtin

import contextlib
import contextvars
import datetime as dt
import hashlib
import io
import json
import logging
import logging.handlers
import pathlib
import re
import time
import typing
import uuid

import pytilpack.python

_logger = logging.getLogger(__name__)


def _json_default(o: typing.Any) -> typing.Any:
    if isinstance(o, dt.datetime):
        return o.isoformat(timespec="milliseconds")
    if isinstance(o, dt.date):
        return o.isoformat()
    if isinstance(o, dt.time):
        return o.isoformat(timespec="milliseconds")
    if isinstance(o, pathlib.Path):
        return str(o)
    if hasattr(o, "__dict__"):
        return o.__dict__
    return str(o)


_exception_history: dict[str, tuple[dt.datetime, int]] = {}


def clear_exception_history() -> None:
    _exception_history.clear()


def stream_handler(
    stream: io.TextIOBase | None = None,
    level: int | None = logging.INFO,
    format: str | None = "[%(levelname)-5s] %(message)s",
) -> logging.Handler:
    handler = logging.StreamHandler(stream)
    if level is not None:
        handler.setLevel(level)
    if format is not None:
        handler.setFormatter(logging.Formatter(format))
    return handler


def file_handler(
    log_path: str | pathlib.Path,
    mode: str = "w",
    encoding: str = "utf-8",
    level: int | None = logging.DEBUG,
    format: str | None = "[%(levelname)-5s] %(message)s",
    max_bytes: int | None = None,
    when: str | None = None,
    backup_count: int = 5,
) -> logging.Handler:
    log_path = pathlib.Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler: logging.Handler
    if max_bytes is not None:
        assert when is None, "max_bytesとwhenは同時に指定できません。"
        handler = logging.handlers.RotatingFileHandler(
            log_path, mode=mode, encoding=encoding, maxBytes=max_bytes, backupCount=backup_count
        )
    elif when is not None:
        handler = logging.handlers.TimedRotatingFileHandler(log_path, when=when, backupCount=backup_count, encoding=encoding)
    else:
        handler = logging.FileHandler(log_path, mode=mode, encoding=encoding)
    if level is not None:
        handler.setLevel(level)
    if format is not None:
        handler.setFormatter(logging.Formatter(format))
    return handler


def multiprocess_file_handler(
    log_path: str | pathlib.Path,
    max_bytes: int,
    backup_count: int = 5,
    encoding: str = "utf-8",
    level: int | None = logging.DEBUG,
    format: str | None = "[%(levelname)-5s] %(message)s",
) -> logging.Handler:
    try:
        import filelock  # pylint: disable=import-outside-toplevel
    except ImportError as e:
        raise ImportError(
            "multiprocess_file_handlerにはfilelockが必要です。`pip install pytilpack[logging]`で導入してください。"
        ) from e
    log_path = pathlib.Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = _MultiprocessRotatingFileHandler(
        log_path,
        filelock.FileLock,
        max_bytes=max_bytes,
        backup_count=backup_count,
        encoding=encoding,
    )
    if level is not None:
        handler.setLevel(level)
    if format is not None:
        handler.setFormatter(logging.Formatter(format))
    return handler


# Windowsでは開いているファイルを移動できないため、ロックの内側でだけログ本体を開き、解放前に閉じる。
class _MultiprocessRotatingFileHandler(logging.handlers.RotatingFileHandler):
    def __init__(
        self,
        log_path: pathlib.Path,
        lock_factory: typing.Callable[[str], contextlib.AbstractContextManager[typing.Any]],
        max_bytes: int,
        backup_count: int,
        encoding: str,
    ) -> None:
        super().__init__(log_path, mode="a", maxBytes=max_bytes, backupCount=backup_count, encoding=encoding, delay=True)
        self.process_lock = lock_factory(f"{self.baseFilename}.lock")

    def emit(self, record: logging.LogRecord) -> None:
        with self.process_lock:
            try:
                super().emit(record)
            finally:
                self._close_stream()

    def _close_stream(self) -> None:
        if self.stream is not None:
            stream, self.stream = self.stream, None
            stream.close()


@contextlib.contextmanager
def timer(name: str, logger: logging.Logger | None = None):
    start_time = time.perf_counter()
    has_error = False
    try:
        yield
    except Exception:
        has_error = True
        raise
    finally:
        elapsed = time.perf_counter() - start_time
        if logger is None:
            logger = _logger
        if has_error:
            logger.warning(f"[{name}] failed in {elapsed:.0f} s. The exception was re-raised; see its traceback for the cause.")
        else:
            logger.info(f"[{name}] done in {elapsed:.0f} s")


def exception_with_dedup(
    logger: logging.Logger,
    exc: BaseException | str,
    msg: str = "Unhandled exception occurred",
    dedup_window: dt.timedelta | None = None,
    dedup_count: int | None = None,
    now: dt.datetime | None = None,
) -> None:
    if dedup_window is None and dedup_count is None:
        dedup_window = dt.timedelta(days=1)
    if now is None:
        now = dt.datetime.now()

    is_exception = isinstance(exc, BaseException)
    parts = (
        ["exception", f"{type(exc).__module__}.{type(exc).__qualname__}", str(exc), msg]
        if is_exception
        else ["str", str(exc), msg]
    )
    raw = json.dumps(parts)
    fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    last = _exception_history.get(fingerprint)
    if last is None:
        should_warn = True
    else:
        last_seen, count = last
        time_expired = dedup_window is not None and (now - last_seen) >= dedup_window
        count_expired = dedup_count is not None and count + 1 >= dedup_count
        should_warn = time_expired or count_expired

    if should_warn:
        if is_exception:
            logger.warning(msg, exc_info=True)
        else:
            logger.warning(msg)
        _exception_history[fingerprint] = (now, 0)
    else:
        logger.info(msg)
        assert last is not None
        _exception_history[fingerprint] = (now, last[1] + 1)


_current_context_id: contextvars.ContextVar[str] = contextvars.ContextVar("_current_context_id", default="")


@contextlib.asynccontextmanager
async def capture_context(
    target_logger: logging.Logger,
    formatter: logging.Formatter,
    level: int = logging.INFO,
) -> typing.AsyncGenerator[typing.Callable[[], str], None]:
    context_id: str = str(uuid.uuid4())
    token = _current_context_id.set(context_id)
    try:
        buffer: io.StringIO = io.StringIO()
        handler: logging.StreamHandler = logging.StreamHandler(buffer)
        handler.setFormatter(formatter)
        handler.setLevel(level)
        handler.addFilter(ContextFilter(context_id))
        target_logger.addHandler(handler)
        try:

            def get_value() -> str:
                return buffer.getvalue()

            yield get_value
        finally:
            target_logger.removeHandler(handler)
            handler.close()
            buffer.close()
    finally:
        _current_context_id.reset(token)


class ContextFilter(logging.Filter):
    def __init__(self, target_id: str) -> None:
        super().__init__()
        self.target_id = target_id

    def filter(self, record: logging.LogRecord) -> bool:
        del record  # noqa
        return _current_context_id.get("") == self.target_id


def jsonify(
    data: typing.Any, indent: int | None = None, truncate: bool = True, model_dump_kwargs: dict[str, typing.Any] | None = None
) -> str:
    if model_dump_kwargs is None:
        model_dump_kwargs = {}
    try:
        if truncate:
            data = truncate_values(data, bytes_to_str=True, model_dump_kwargs=model_dump_kwargs)
        else:
            data = pytilpack.python.pydantic_to_dict(data, **model_dump_kwargs)

        separators = None if indent is not None else (",", ":")
        return json.dumps(data, ensure_ascii=False, indent=indent, separators=separators, default=_json_default)
    except Exception:
        _logger.warning("jsonify失敗。repr()の文字列を返して処理を続ける（対応不要）", exc_info=True)
        return repr(data)


def truncate_values(
    data: typing.Any,
    max_str_len: int = 100,
    max_bytes_len: int = 100,
    bytes_to_str: bool = False,
    model_dump_kwargs: dict[str, typing.Any] | None = None,
    max_num_list_len: int = 3,
) -> typing.Any:
    if model_dump_kwargs is None:
        model_dump_kwargs = {}
    data = pytilpack.python.pydantic_to_dict(data, **model_dump_kwargs)

    if isinstance(data, str):
        if len(data) > max_str_len:
            return data[:max_str_len] + "..."
        return data
    if isinstance(data, bytes):
        if bytes_to_str:
            decoded = data.decode("utf-8", errors="replace")
            if len(decoded) > max_str_len:
                return decoded[:max_str_len] + "..."
            return decoded
        else:
            if len(data) > max_bytes_len:
                return data[:max_bytes_len] + b"..."
            return data
    if isinstance(data, dict):
        return {
            truncate_values(k, max_str_len, max_bytes_len, bytes_to_str, model_dump_kwargs, max_num_list_len): truncate_values(
                v, max_str_len, max_bytes_len, bytes_to_str, model_dump_kwargs, max_num_list_len
            )
            for k, v in data.items()
        }
    if isinstance(data, list):
        if len(data) > max_num_list_len and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in data):
            return [*data[:max_num_list_len], "..."]
        return [
            truncate_values(item, max_str_len, max_bytes_len, bytes_to_str, model_dump_kwargs, max_num_list_len)
            for item in data
        ]
    if isinstance(data, tuple):
        return tuple(
            truncate_values(item, max_str_len, max_bytes_len, bytes_to_str, model_dump_kwargs, max_num_list_len)
            for item in data
        )
    return data


REDACTED = "[REDACTED]"

_REDACT_HEADER_PATTERN = re.compile(r"(?i)\b((?:proxy-)?authorization)([ \t]*[:=][ \t]*)\S[^\r\n]*")
_REDACT_NAMED_PATTERN = re.compile(
    r"""(?i)(["']?)(\b[\w-]*?(?:api[ _-]?key|token|secret|password)[\w-]*)\1([ \t]*[:=][ \t]*)"""
    r"""("(?:\\.|[^"\\\r\n])*"|'(?:\\.|[^'\\\r\n])*'|\[REDACTED\][^\s,;&"')}\]]*|[^\s,;&"')}\]]+)"""
)
_REDACT_KEYLIKE_PATTERN = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{32,}(?![A-Za-z0-9_-])")


def redact_secrets(text: str) -> str:
    if not text:
        return text
    text = _REDACT_HEADER_PATTERN.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", text)
    text = _REDACT_NAMED_PATTERN.sub(_redact_named_value, text)
    return _REDACT_KEYLIKE_PATTERN.sub(REDACTED, text)


def _redact_named_value(match: re.Match[str]) -> str:
    quote, key, separator, value = match.groups()
    value = f"{value[0]}{REDACTED}{value[0]}" if value[:1] in ("'", '"') else REDACTED
    return f"{quote}{key}{quote}{separator}{value}"
