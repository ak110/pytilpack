"""ログ関連。"""

# pylint: disable=redefined-builtin

import contextlib
import io
import logging
import pathlib
import time


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
