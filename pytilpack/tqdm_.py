"""tqdm用のユーティリティ集。"""

import contextlib
import io
import logging
import sys
import typing

import tqdm


class TqdmStreamHandler(logging.StreamHandler):
    """tqdm対応のStreamHandler。

    使用例::
        import pytilpack.tqdm_

        logging.basicConfig(
            level=logging.INFO,
            format="[%(levelname)s] %(message)s",
            handlers=[pytilpack.tqdm_.TqdmStreamHandler()],
        )

    """

    @typing.override
    def emit(self, record):
        with tqdm.tqdm.external_write_mode(file=self.stream):
            super().emit(record)


@contextlib.contextmanager
def capture(capture_stdout: bool = True, capture_stderr: bool = True):
    """標準出力、標準エラー出力をキャプチャして最後にまとめて(tqdm対応で)出力する。

    Args:
        capture_stdout: 標準出力をキャプチャするかどうか。
        capture_stderr: 標準エラー出力をキャプチャするかどうか。

    """
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    try:
        with (
            (
                contextlib.redirect_stdout(stdout_buffer)
                if capture_stdout
                else contextlib.nullcontext()
            ),
            (
                contextlib.redirect_stderr(stderr_buffer)
                if capture_stderr
                else contextlib.nullcontext()
            ),
        ):
            yield
    finally:
        stdout = stdout_buffer.getvalue()
        stderr = stderr_buffer.getvalue()
        if len(stdout) > 0:
            tqdm.tqdm.write(stdout, end="", file=sys.stdout)
        if len(stderr) > 0:
            tqdm.tqdm.write(stderr, end="", file=sys.stderr)
