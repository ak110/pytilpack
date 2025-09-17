"""ログ関連。"""

# pylint: disable=redefined-builtin

import contextlib
import contextvars
import datetime
import hashlib
import io
import logging
import pathlib
import time
import typing
import uuid

_exception_history: dict[str, datetime.datetime] = {}
"""例外フィンガープリント → 最終発生時刻。"""


def stream_handler(
    stream: io.TextIOBase | None = None,
    level: int | None = logging.INFO,
    format: str | None = "[%(levelname)-5s] %(message)s",
) -> logging.Handler:
    """標準エラー出力用のハンドラを作成。"""
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
) -> logging.Handler:
    """ファイル出力用のハンドラを作成。"""
    log_path = pathlib.Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, mode=mode, encoding=encoding)
    if level is not None:
        handler.setLevel(level)
    if format is not None:
        handler.setFormatter(logging.Formatter(format))
    return handler


@contextlib.contextmanager
def timer(name, logger: logging.Logger | None = None):
    """処理時間の計測＆表示。"""
    start_time = time.perf_counter()
    has_error = False
    try:
        yield
    except Exception as e:
        has_error = True
        raise e
    finally:
        elapsed = time.perf_counter() - start_time
        if logger is None:
            logger = logging.getLogger(__name__)
        if has_error:
            logger.warning(f"[{name}] failed in {elapsed:.0f} s")
        else:
            logger.info(f"[{name}] done in {elapsed:.0f} s")


def exception_with_dedup(
    logger: logging.Logger,
    exc: BaseException,
    msg: str = "Unhandled exception occurred",
    dedup_window: datetime.timedelta | None = None,
    now: datetime.datetime | None = None,
) -> None:
    """同一 fingerprint が dedup_window 内にあれば INFO、そうでなければ WARN で exc_info=True 付きでログ出力する。

    Args:
        logger: 出力先ロガー
        exc: 例外
        msg: ログメッセージ。fingerprint にも含まれる。
        dedup_window: 同一エラーとみなす時間幅。デフォルト 24 時間。
        now: 現在時刻。
    """
    if dedup_window is None:
        dedup_window = datetime.timedelta(days=1)
    if now is None:
        now = datetime.datetime.now()

    raw = f"{exc.__class__.__name__}:{str(exc)}:{msg}"
    fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    last_seen = _exception_history.get(fingerprint)
    if last_seen is not None and (now - last_seen) < dedup_window:
        logger.info(msg)
    else:
        logger.warning(msg, exc_info=True)

    _exception_history[fingerprint] = now


_current_context_id: contextvars.ContextVar[str] = contextvars.ContextVar("_current_context_id", default="")


@contextlib.asynccontextmanager
async def capture_context(
    target_logger: logging.Logger,
    formatter: logging.Formatter,
    level: int = logging.INFO,
) -> typing.AsyncGenerator[typing.Callable[[], str], None]:
    """指定ロガーに対して“この非同期コンテキストのログだけ”をStringIOへ集約する。

    Args:
        target_logger: ハンドラを一時的に取り付ける対象のロガー。
        formatter: このキャプチャ専用のフォーマッタ。
        level: このキャプチャハンドラのログレベル。

    Yields:
        get_value: これまでにバッファへ書かれた文字列を返す関数。
    """
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
    """_context_idと一致するログだけを通すフィルタ。"""

    def __init__(self, target_id: str) -> None:
        super().__init__()
        self.target_id = target_id

    def filter(self, record: logging.LogRecord) -> bool:
        del record  # noqa
        return _current_context_id.get("") == self.target_id
