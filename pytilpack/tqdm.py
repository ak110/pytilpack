__lazy_modules__ = ["contextlib", "io", "logging", "sys", "tqdm", "typing"]

import contextlib
import io
import logging
import sys
import typing

import tqdm


class TqdmStreamHandler(logging.StreamHandler):
    @typing.override
    def emit(self, record):
        with tqdm.tqdm.external_write_mode(file=self.stream):
            super().emit(record)


@contextlib.contextmanager
def capture(capture_stdout: bool = True, capture_stderr: bool = True):
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    try:
        with (
            contextlib.redirect_stdout(stdout_buffer) if capture_stdout else contextlib.nullcontext(),
            contextlib.redirect_stderr(stderr_buffer) if capture_stderr else contextlib.nullcontext(),
        ):
            yield
    finally:
        stdout = stdout_buffer.getvalue()
        stderr = stderr_buffer.getvalue()
        if len(stdout) > 0:
            tqdm.tqdm.write(stdout, end="", file=sys.stdout)
        if len(stderr) > 0:
            tqdm.tqdm.write(stderr, end="", file=sys.stderr)
