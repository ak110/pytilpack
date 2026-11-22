import asyncio
import concurrent.futures
import datetime as dt
import io
import json
import logging
import logging.handlers
import multiprocessing
import pathlib
import types
import typing

import filelock
import pytest

import pytilpack.logging


@pytest.fixture(autouse=True)
def _clear_exception_history() -> typing.Generator[None, None, None]:
    pytilpack.logging.clear_exception_history()
    yield
    pytilpack.logging.clear_exception_history()


def test_logging(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture) -> None:
    logger = logging.getLogger(__name__)
    try:
        logger.setLevel(logging.DEBUG)
        logger.addHandler(pytilpack.logging.stream_handler())
        logger.addHandler(pytilpack.logging.file_handler(tmp_path / "test.log"))

        logger.debug("debug")
        logger.info("info")
        logger.warning("warning")

        assert (tmp_path / "test.log").read_text(encoding="utf-8") == "[DEBUG] debug\n[INFO ] info\n[WARNING] warning\n"
        assert capsys.readouterr().err == "[INFO ] info\n[WARNING] warning\n"
    finally:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()


def test_timer(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    ticks = iter((100, 103, 100, 103))
    monkeypatch.setattr(pytilpack.logging, "time", types.SimpleNamespace(perf_counter=lambda: next(ticks)))
    with caplog.at_level(logging.INFO), pytilpack.logging.timer("test"):
        pass
    assert caplog.record_tuples == [("pytilpack.logging", logging.INFO, "[test] done in 3 s")]

    caplog.clear()
    error = ValueError("timer failure")
    with caplog.at_level(logging.INFO), pytest.raises(ValueError) as caught, pytilpack.logging.timer("test"):
        raise error
    assert caught.value is error
    (record,) = caplog.records
    assert record.name == "pytilpack.logging"
    assert record.levelno == logging.WARNING
    assert record.message.startswith("[test] failed in 3 s")


def test_exception_with_dedup(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)

    now = dt.datetime(2023, 1, 1, 12, 0, 0)
    dedup_window = dt.timedelta(hours=1)

    exc1 = ValueError("test error")
    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, exc1, msg="テストエラー", dedup_window=dedup_window, now=now)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].message == "テストエラー"
    assert caplog.records[0].exc_info is not None

    caplog.clear()

    now2 = now + dt.timedelta(minutes=30)
    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, exc1, msg="テストエラー", dedup_window=dedup_window, now=now2)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "INFO"
    assert caplog.records[0].message == "テストエラー"
    assert caplog.records[0].exc_info is None

    caplog.clear()

    now3 = now + dt.timedelta(hours=2)
    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, exc1, msg="テストエラー", dedup_window=dedup_window, now=now3)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].message == "テストエラー"
    assert caplog.records[0].exc_info is not None

    caplog.clear()

    exc2 = RuntimeError("test error")
    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, exc2, msg="テストエラー", dedup_window=dedup_window, now=now3)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].message == "テストエラー"
    assert caplog.records[0].exc_info is not None

    caplog.clear()

    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, exc1, msg="別のテストエラー", dedup_window=dedup_window, now=now3)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].message == "別のテストエラー"
    assert caplog.records[0].exc_info is not None

    caplog.clear()

    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, ValueError("新しいエラー"))

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].message == "Unhandled exception occurred"
    assert caplog.records[0].exc_info is not None


def test_exception_with_dedup_str(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("test_logger_str")
    logger.setLevel(logging.DEBUG)

    now = dt.datetime(2023, 1, 1, 12, 0, 0)
    dedup_window = dt.timedelta(hours=1)

    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, "接続エラー", msg="テストエラー", dedup_window=dedup_window, now=now)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].message == "テストエラー"
    assert caplog.records[0].exc_info is None

    caplog.clear()

    now2 = now + dt.timedelta(minutes=30)
    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, "接続エラー", msg="テストエラー", dedup_window=dedup_window, now=now2)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "INFO"

    caplog.clear()

    now3 = now + dt.timedelta(hours=2)
    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, "接続エラー", msg="テストエラー", dedup_window=dedup_window, now=now3)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].exc_info is None

    caplog.clear()

    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, "別のエラー", msg="テストエラー", dedup_window=dedup_window, now=now3)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"


def test_exception_with_dedup_count(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("test_logger_count")
    logger.setLevel(logging.DEBUG)

    now = dt.datetime(2023, 1, 1, 12, 0, 0)
    exc = ValueError("test error")

    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, exc, dedup_count=3, now=now)
        assert caplog.records[-1].levelname == "WARNING"

        pytilpack.logging.exception_with_dedup(logger, exc, dedup_count=3, now=now)
        assert caplog.records[-1].levelname == "INFO"

        pytilpack.logging.exception_with_dedup(logger, exc, dedup_count=3, now=now)
        assert caplog.records[-1].levelname == "INFO"

        pytilpack.logging.exception_with_dedup(logger, exc, dedup_count=3, now=now)
        assert caplog.records[-1].levelname == "WARNING"

        pytilpack.logging.exception_with_dedup(logger, exc, dedup_count=3, now=now)
        assert caplog.records[-1].levelname == "INFO"


def test_exception_with_dedup_count_str(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("test_logger_count_str")
    logger.setLevel(logging.DEBUG)

    now = dt.datetime(2023, 1, 1, 12, 0, 0)

    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, "timeout", dedup_count=2, now=now)
        assert caplog.records[-1].levelname == "WARNING"
        assert caplog.records[-1].exc_info is None

        pytilpack.logging.exception_with_dedup(logger, "timeout", dedup_count=2, now=now)
        assert caplog.records[-1].levelname == "INFO"

        pytilpack.logging.exception_with_dedup(logger, "timeout", dedup_count=2, now=now)
        assert caplog.records[-1].levelname == "WARNING"
        assert caplog.records[-1].exc_info is None


def test_exception_with_dedup_both_windows(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("test_logger_both")
    logger.setLevel(logging.DEBUG)

    now = dt.datetime(2023, 1, 1, 12, 0, 0)
    dedup_window = dt.timedelta(hours=1)
    exc = ValueError("test error")

    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, exc, dedup_window=dedup_window, dedup_count=5, now=now)
        assert caplog.records[-1].levelname == "WARNING"

        for _ in range(3):
            pytilpack.logging.exception_with_dedup(logger, exc, dedup_window=dedup_window, dedup_count=5, now=now)
            assert caplog.records[-1].levelname == "INFO"

        now2 = now + dt.timedelta(hours=2)
        pytilpack.logging.exception_with_dedup(logger, exc, dedup_window=dedup_window, dedup_count=5, now=now2)
        assert caplog.records[-1].levelname == "WARNING"

    caplog.clear()
    pytilpack.logging.clear_exception_history()

    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, exc, dedup_window=dedup_window, dedup_count=3, now=now)
        assert caplog.records[-1].levelname == "WARNING"

        for _ in range(2):
            pytilpack.logging.exception_with_dedup(logger, exc, dedup_window=dedup_window, dedup_count=3, now=now)
            assert caplog.records[-1].levelname == "INFO"

        pytilpack.logging.exception_with_dedup(logger, exc, dedup_window=dedup_window, dedup_count=3, now=now)
        assert caplog.records[-1].levelname == "WARNING"


def _assert_second_call_warns(
    caplog: pytest.LogCaptureFixture,
    first: tuple[BaseException | str, str],
    second: tuple[BaseException | str, str],
) -> None:
    logger = logging.getLogger("test_logger_fingerprint")
    logger.setLevel(logging.DEBUG)
    now = dt.datetime(2023, 1, 1, 12, 0, 0)
    pytilpack.logging.clear_exception_history()
    caplog.clear()
    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, first[0], msg=first[1], now=now)
        pytilpack.logging.exception_with_dedup(logger, second[0], msg=second[1], now=now)
    assert [r.levelname for r in caplog.records] == ["WARNING", "WARNING"]
    if isinstance(second[0], BaseException):
        assert caplog.records[-1].exc_info is not None
    else:
        assert caplog.records[-1].exc_info is None


def test_exception_with_dedup_distinguishes_exception_and_str(caplog: pytest.LogCaptureFixture) -> None:
    _assert_second_call_warns(caplog, (ValueError("x"), "y"), ("ValueError:x", "y"))
    _assert_second_call_warns(caplog, ("ValueError:x", "y"), (ValueError("x"), "y"))


def test_exception_with_dedup_distinguishes_element_boundaries(caplog: pytest.LogCaptureFixture) -> None:
    _assert_second_call_warns(caplog, ("a:b", "c"), ("a", "b:c"))
    _assert_second_call_warns(caplog, (ValueError("a:b"), "c"), (ValueError("a"), "b:c"))


def test_exception_with_dedup_distinguishes_same_name_classes(caplog: pytest.LogCaptureFixture) -> None:

    class _First:
        class Error(Exception):
            pass

    class _Second:
        class Error(Exception):
            pass

    assert _First.Error.__name__ == _Second.Error.__name__
    _assert_second_call_warns(caplog, (_First.Error("e"), "m"), (_Second.Error("e"), "m"))


@pytest.mark.asyncio
async def test_capture_context() -> None:
    logger = logging.getLogger("test_capture_context")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(levelname)s] %(message)s")

    original_handlers = logger.handlers[:]
    captured_content = ""
    async with pytilpack.logging.capture_context(logger, formatter, logging.INFO) as get_value:
        capture_handlers = [handler for handler in logger.handlers if handler not in original_handlers]
        assert len(capture_handlers) == 1
        assert get_value() == ""

        logger.info("テストメッセージ1")
        logger.debug("デバッグメッセージ")
        logger.warning("テストメッセージ2")

        captured_content = get_value()
        assert "[INFO] テストメッセージ1\n" in captured_content
        assert "[WARNING] テストメッセージ2\n" in captured_content
        assert "デバッグメッセージ" not in captured_content

    assert all(handler not in logger.handlers for handler in capture_handlers)


@pytest.mark.asyncio
async def test_capture_context_multiple_tasks() -> None:
    logger = logging.getLogger("test_capture_context_multi")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(levelname)s] %(message)s")

    entered = [asyncio.Event(), asyncio.Event()]
    emitted = [asyncio.Event(), asyncio.Event()]

    async def capture(index: int) -> str:
        async with pytilpack.logging.capture_context(logger, formatter, logging.INFO) as get_value:
            entered[index].set()
            await entered[1 - index].wait()
            logger.info("タスク%d", index)
            if index == 0:
                logger.warning("タスク0の警告")
            else:
                logger.error("タスク1のエラー")
            emitted[index].set()
            await emitted[1 - index].wait()
            return get_value()

    async with asyncio.timeout(5):
        result1, result2 = await asyncio.gather(capture(0), capture(1))
    assert result1.splitlines() == ["[INFO] タスク0", "[WARNING] タスク0の警告"]
    assert result2.splitlines() == ["[INFO] タスク1", "[ERROR] タスク1のエラー"]


@pytest.mark.asyncio
async def test_capture_context_nested() -> None:
    logger = logging.getLogger("test_capture_context_nested")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(levelname)s] %(message)s")

    async with pytilpack.logging.capture_context(logger, formatter, logging.INFO) as outer_get_value:
        logger.info("外側のメッセージ1")

        async with pytilpack.logging.capture_context(logger, formatter, logging.WARNING) as inner_get_value:
            logger.info("内側のメッセージ（INFOレベル）")
            logger.warning("内側のメッセージ（WARNINGレベル）")

            inner_captured = inner_get_value()
            assert "内側のメッセージ（WARNINGレベル）" in inner_captured
            assert "内側のメッセージ（INFOレベル）" not in inner_captured
            assert "外側のメッセージ1" not in inner_captured

        logger.info("外側のメッセージ2")

        outer_captured = outer_get_value()
        assert "外側のメッセージ1" in outer_captured
        assert "外側のメッセージ2" in outer_captured
        assert "内側のメッセージ（WARNINGレベル）" not in outer_captured


@pytest.mark.parametrize(
    "data,max_str_len,max_bytes_len,bytes_to_str,expected",
    [
        ("short", 100, 100, False, "short"),
        ("a" * 150, 100, 100, False, "a" * 100 + "..."),
        (b"short", 100, 100, False, b"short"),
        (b"x" * 150, 100, 100, False, b"x" * 100 + b"..."),
        (b"short", 100, 100, True, "short"),
        (b"x" * 150, 100, 100, True, "x" * 100 + "..."),
        ({"key": "a" * 150}, 100, 100, False, {"key": "a" * 100 + "..."}),
        ({"k1": "short", "k2": "b" * 150}, 100, 100, False, {"k1": "short", "k2": "b" * 100 + "..."}),
        ({"k1": b"short", "k2": b"x" * 150}, 100, 100, True, {"k1": "short", "k2": "x" * 100 + "..."}),
        (["short", "a" * 150], 100, 100, False, ["short", "a" * 100 + "..."]),
        ([b"short", b"x" * 150], 100, 100, True, ["short", "x" * 100 + "..."]),
        (("short", "a" * 150), 100, 100, False, ("short", "a" * 100 + "...")),
        ((b"short", b"x" * 150), 100, 100, True, ("short", "x" * 100 + "...")),
        (
            {"outer": {"inner": "a" * 150}},
            100,
            100,
            False,
            {"outer": {"inner": "a" * 100 + "..."}},
        ),
        (
            {"list": ["a" * 150, b"x" * 150]},
            100,
            100,
            False,
            {"list": ["a" * 100 + "...", b"x" * 100 + b"..."]},
        ),
        (
            {"list": [b"a" * 150, b"x" * 150]},
            100,
            100,
            True,
            {"list": ["a" * 100 + "...", "x" * 100 + "..."]},
        ),
        (123, 100, 100, False, 123),
        (None, 100, 100, False, None),
        (True, 100, 100, False, True),
    ],
)
def test_truncate_values(
    data: typing.Any,
    max_str_len: int,
    max_bytes_len: int,
    bytes_to_str: bool,
    expected: typing.Any,
) -> None:
    actual = pytilpack.logging.truncate_values(data, max_str_len, max_bytes_len, bytes_to_str)
    assert actual == expected


@pytest.mark.parametrize(
    "obj,indent,truncate,expected",
    [
        ({"key": "value"}, None, False, '{"key":"value"}'),
        ({"key": "値"}, None, False, '{"key":"値"}'),
        ({"key": "value"}, 2, False, '{\n  "key": "value"\n}'),
        ({"key": "a" * 150}, None, True, '{"key":"' + "a" * 100 + '..."}'),
        ({"key": b"x" * 150}, None, True, '{"key":"' + "x" * 100 + '..."}'),
        ({"key": "a" * 150}, None, False, '{"key":"' + "a" * 150 + '"}'),
        ([1, 2, 3], None, False, "[1,2,3]"),
        ({"list": ["a" * 150, "b"]}, None, True, '{"list":["' + "a" * 100 + '...","b"]}'),
        ({"dt": dt.datetime(2023, 1, 1, 12, 0, 0, 123000)}, None, False, '{"dt":"2023-01-01T12:00:00.123"}'),
        ({"date": dt.date(2023, 1, 1)}, None, False, '{"date":"2023-01-01"}'),
        (
            {"path": pathlib.Path("/tmp/test")},
            None,
            False,
            '{"path":' + json.dumps(str(pathlib.Path("/tmp/test"))) + "}",
        ),
    ],
)
def test_jsonify(
    obj: typing.Any,
    indent: int | None,
    truncate: bool,
    expected: str,
) -> None:
    actual = pytilpack.logging.jsonify(obj, indent, truncate)
    assert actual == expected


def test_redact_secrets_multiline() -> None:
    key = "sk_live_" + "A1b2C3d4" * 4
    text = (
        "HTTPError 401 Unauthorized: request to https://api.example.com/v1/items failed\n"
        "Authorization: Bearer abc.def.ghi\n"
        "Proxy-Authorization: Basic dXNlcjpwYXNz\n"
        f'{{"error_code": "E1234", "api_key": "{key}", "message": "invalid credentials"}}\n'
        "retry with password=hunter2; ACCESS_TOKEN = 'tok en' (code=E42)\n"
    )
    actual = pytilpack.logging.redact_secrets(text)
    assert actual == (
        "HTTPError 401 Unauthorized: request to https://api.example.com/v1/items failed\n"
        "Authorization: [REDACTED]\n"
        "Proxy-Authorization: [REDACTED]\n"
        '{"error_code": "E1234", "api_key": "[REDACTED]", "message": "invalid credentials"}\n'
        "retry with password=[REDACTED]; ACCESS_TOKEN = '[REDACTED]' (code=E42)\n"
    )
    assert key not in actual


@pytest.mark.parametrize(
    "text,expected",
    [
        ("id " + "a" * 31 + " end", "id " + "a" * 31 + " end"),
        ("id " + "a" * 32 + " end", "id [REDACTED] end"),
        ("id " + "x_-9" * 8 + ".", "id [REDACTED]."),
        ('secret="a b c" next', 'secret="[REDACTED]" next'),
        ("token: 'x y'", "token: '[REDACTED]'"),
        ("API KEY: abc", "API KEY: [REDACTED]"),
        ("Api-Key=abc", "Api-Key=[REDACTED]"),
        ("apikey=abc", "apikey=[REDACTED]"),
        ("Password = abc", "Password = [REDACTED]"),
        ("authorization=Token abc def", "authorization=[REDACTED]"),
        ("token expired at 12:00", "token expired at 12:00"),
        ("", ""),
        ("plain error message\nline 2\r\n", "plain error message\nline 2\r\n"),
        ("Authorization: [REDACTED]abc\n", "Authorization: [REDACTED]\n"),
        ('password="[REDACTED]abc" code=E42', 'password="[REDACTED]" code=E42'),
        ("password=[REDACTED]abc code=E42", "password=[REDACTED] code=E42"),
        (json.dumps({"password": 'abc"def ghi', "code": "E42"}), '{"password": "[REDACTED]", "code": "E42"}'),
        ("token: 'it\\'s secret' code=E42", "token: '[REDACTED]' code=E42"),
        ("(password=abc) code=E42", "(password=[REDACTED]) code=E42"),
        ("[token=abc] code=E42", "[token=[REDACTED]] code=E42"),
        ("{secret=abc} code=E42", "{secret=[REDACTED]} code=E42"),
    ],
)
def test_redact_secrets(text: str, expected: str) -> None:
    assert pytilpack.logging.redact_secrets(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Authorization: Bearer abc\npassword='p w' api_key=k " + "z" * 40,
        '"token": "t", Proxy-Authorization = Basic xyz',
    ],
)
def test_redact_secrets_idempotent(text: str) -> None:
    once = pytilpack.logging.redact_secrets(text)
    assert once != text
    assert pytilpack.logging.redact_secrets(once) == once


def _write_shared_log(log_path: pathlib.Path, writer: str, count: int) -> None:
    logger = logging.getLogger(f"{__name__}.shared_writer_{writer}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = pytilpack.logging.multiprocess_file_handler(log_path, max_bytes=512, backup_count=1000, format="%(message)s")
    logger.addHandler(handler)
    try:
        for i in range(count):
            logger.info(f"{writer}-{i:04d}-{'x' * 40}")
    finally:
        logger.removeHandler(handler)
        handler.close()


def _read_generations(log_path: pathlib.Path) -> list[str]:
    paths = sorted(
        log_path.parent.glob(f"{log_path.name}.*[0-9]"), key=lambda path: int(path.suffix.removeprefix(".")), reverse=True
    )
    return [line for path in [*paths, log_path] for line in path.read_text(encoding="utf-8").splitlines()]


def test_multiprocess_file_handler_processes(tmp_path: pathlib.Path) -> None:
    log_path = tmp_path / "shared.log"
    count = 200
    # spawnで起動し、親のハンドラやロックを引き継がない独立したwriterとする（Windowsと同じ起動方式）
    with concurrent.futures.ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context("spawn")) as executor:
        futures = [executor.submit(_write_shared_log, log_path, writer, count) for writer in ("a", "b")]
        for future in futures:
            future.result(timeout=50)

    lines = _read_generations(log_path)
    assert sorted(lines) == sorted(f"{writer}-{i:04d}-{'x' * 40}" for writer in ("a", "b") for i in range(count))
    for writer in ("a", "b"):
        assert [line for line in lines if line.startswith(f"{writer}-")] == [
            f"{writer}-{i:04d}-{'x' * 40}" for i in range(count)
        ]
    assert len(list(tmp_path.glob("shared.log.*[0-9]"))) > 1


def test_multiprocess_file_handler_rotation(tmp_path: pathlib.Path) -> None:
    log_path = tmp_path / "rotate.log"
    log_path.write_text("existing\n", encoding="utf-8")
    handlers = [
        pytilpack.logging.multiprocess_file_handler(log_path, max_bytes=40, backup_count=2, format="%(message)s")
        for _ in range(2)
    ]
    try:
        assert log_path.read_text(encoding="utf-8") == "existing\n"
        for i, message in enumerate(("a" * 20, "b" * 22, "c" * 24, "d" * 26)):
            handlers[i % 2].handle(logging.makeLogRecord({"msg": message, "levelno": logging.INFO}))

        assert {
            path.name: path.read_text(encoding="utf-8").splitlines()
            for path in tmp_path.iterdir()
            if not path.name.endswith(".lock")
        } == {"rotate.log": ["d" * 26], "rotate.log.1": ["c" * 24], "rotate.log.2": ["b" * 22]}
    finally:
        for handler in handlers:
            handler.close()


class _RecordingStream(io.StringIO):
    def __init__(self, events: list[str], initial: str, fail_write: bool) -> None:
        super().__init__(initial)
        self.seek(0, io.SEEK_END)
        self.events = events
        self.fail_write = fail_write

    def write(self, s: str) -> int:
        if self.fail_write:
            raise OSError(f"write failed: {s!r}")
        return super().write(s)

    def close(self) -> None:
        self.events.append("close")
        super().close()


class _RecordingLock:
    def __init__(self, lock: typing.Any, events: list[str]) -> None:
        self.lock = lock
        self.events = events

    def __enter__(self) -> None:
        self.lock.acquire()
        self.events.append("acquire")

    def __exit__(self, *exc_info: typing.Any) -> None:
        self.events.append("release")
        self.lock.release()


@pytest.mark.parametrize("failure", ["write", "rotate"])
def test_multiprocess_file_handler_failure(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    handler = pytilpack.logging.multiprocess_file_handler(tmp_path / "fail.log", max_bytes=1024, format="%(message)s")
    assert isinstance(handler, logging.handlers.RotatingFileHandler)
    events: list[str] = []
    errors: list[logging.LogRecord] = []

    def open_stream() -> _RecordingStream:
        initial = "x" * 2048 if failure == "rotate" else ""
        return _RecordingStream(events, initial, fail_write=failure == "write")

    def fail_rotate(source: str, dest: str) -> None:
        raise OSError(f"rotate failed: {source} -> {dest}")

    monkeypatch.setattr(handler, "_open", open_stream)
    monkeypatch.setattr(handler, "handleError", errors.append)
    if failure == "rotate":
        monkeypatch.setattr(handler, "rotate", fail_rotate)
    monkeypatch.setattr(handler, "process_lock", _RecordingLock(vars(handler)["process_lock"], events))
    try:
        handler.handle(logging.makeLogRecord({"msg": "record", "levelno": logging.INFO}))
        assert len(errors) == 1
        assert events == ["acquire", "close", "release"]
        assert handler.stream is None
        lock = filelock.FileLock(f"{tmp_path / 'fail.log'}.lock")
        lock.acquire(timeout=0)
        lock.release()
    finally:
        handler.close()
