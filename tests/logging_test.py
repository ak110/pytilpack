"""テストコード。"""

import asyncio
import datetime
import logging
import pathlib
import typing

import pytest

import pytilpack.logging


@pytest.fixture(autouse=True)
def _clear_exception_history() -> typing.Generator[None, None, None]:
    """テストごとに例外重複排除の履歴をクリアする。"""
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


def test_timer(caplog: pytest.LogCaptureFixture) -> None:
    """timerコンテキストマネージャの成功・失敗テスト。"""
    # 成功時: INFOレベルで "done" と出力
    with caplog.at_level(logging.INFO), pytilpack.logging.timer("test"):
        pass
    assert caplog.record_tuples == [("pytilpack.logging", logging.INFO, "[test] done in 0 s")]

    caplog.clear()

    # 失敗時: WARNINGレベルで "failed" と出力
    with caplog.at_level(logging.INFO):
        try:
            with pytilpack.logging.timer("test"):
                raise ValueError()
        except ValueError:
            pass
    assert caplog.record_tuples == [("pytilpack.logging", logging.WARNING, "[test] failed in 0 s")]


def test_exception_with_dedup(caplog: pytest.LogCaptureFixture) -> None:
    """exception_with_dedupのテスト。"""
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)

    # 固定時刻を設定
    now = datetime.datetime(2023, 1, 1, 12, 0, 0)
    dedup_window = datetime.timedelta(hours=1)

    # 最初の例外は WARNING レベルで出力される
    exc1 = ValueError("test error")
    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, exc1, msg="テストエラー", dedup_window=dedup_window, now=now)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].message == "テストエラー"
    assert caplog.records[0].exc_info is not None

    caplog.clear()

    # 同じ例外を dedup_window 内で再度発生させると INFO レベルで出力される
    now2 = now + datetime.timedelta(minutes=30)
    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, exc1, msg="テストエラー", dedup_window=dedup_window, now=now2)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "INFO"
    assert caplog.records[0].message == "テストエラー"
    assert caplog.records[0].exc_info is None

    caplog.clear()

    # dedup_window を超えた後は再び WARNING レベルで出力される
    now3 = now + datetime.timedelta(hours=2)
    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, exc1, msg="テストエラー", dedup_window=dedup_window, now=now3)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].message == "テストエラー"
    assert caplog.records[0].exc_info is not None

    caplog.clear()

    # 異なる例外クラスは別として扱われる
    exc2 = RuntimeError("test error")
    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, exc2, msg="テストエラー", dedup_window=dedup_window, now=now3)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].message == "テストエラー"
    assert caplog.records[0].exc_info is not None

    caplog.clear()

    # 異なるメッセージも別として扱われる
    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, exc1, msg="別のテストエラー", dedup_window=dedup_window, now=now3)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].message == "別のテストエラー"
    assert caplog.records[0].exc_info is not None

    caplog.clear()

    # デフォルト値のテスト（dedup_window=None, now=None）
    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, ValueError("新しいエラー"))

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].message == "Unhandled exception occurred"
    assert caplog.records[0].exc_info is not None


def test_exception_with_dedup_str(caplog: pytest.LogCaptureFixture) -> None:
    """exception_with_dedupに文字列を渡すテスト。"""
    logger = logging.getLogger("test_logger_str")
    logger.setLevel(logging.DEBUG)

    now = datetime.datetime(2023, 1, 1, 12, 0, 0)
    dedup_window = datetime.timedelta(hours=1)

    # 文字列の場合も WARNING で出力されるが exc_info は付かない
    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, "接続エラー", msg="テストエラー", dedup_window=dedup_window, now=now)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].message == "テストエラー"
    assert caplog.records[0].exc_info is None

    caplog.clear()

    # 同じ文字列を dedup_window 内で再度渡すと INFO
    now2 = now + datetime.timedelta(minutes=30)
    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, "接続エラー", msg="テストエラー", dedup_window=dedup_window, now=now2)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "INFO"

    caplog.clear()

    # dedup_window を超えた後は再び WARNING
    now3 = now + datetime.timedelta(hours=2)
    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, "接続エラー", msg="テストエラー", dedup_window=dedup_window, now=now3)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].exc_info is None

    caplog.clear()

    # 異なる文字列は別として扱われる
    with caplog.at_level(logging.INFO):
        pytilpack.logging.exception_with_dedup(logger, "別のエラー", msg="テストエラー", dedup_window=dedup_window, now=now3)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"


def test_exception_with_dedup_count(caplog: pytest.LogCaptureFixture) -> None:
    """exception_with_dedupの個数窓テスト。"""
    logger = logging.getLogger("test_logger_count")
    logger.setLevel(logging.DEBUG)

    now = datetime.datetime(2023, 1, 1, 12, 0, 0)
    exc = ValueError("test error")

    # dedup_count=3: WARNING → 2回INFO → WARNING → ... (3回ごとにWARNING)
    with caplog.at_level(logging.INFO):
        # 1回目: WARNING
        pytilpack.logging.exception_with_dedup(logger, exc, dedup_count=3, now=now)
        assert caplog.records[-1].levelname == "WARNING"

        # 2回目: INFO
        pytilpack.logging.exception_with_dedup(logger, exc, dedup_count=3, now=now)
        assert caplog.records[-1].levelname == "INFO"

        # 3回目: INFO
        pytilpack.logging.exception_with_dedup(logger, exc, dedup_count=3, now=now)
        assert caplog.records[-1].levelname == "INFO"

        # 4回目: WARNING (3回目なのでリセット)
        pytilpack.logging.exception_with_dedup(logger, exc, dedup_count=3, now=now)
        assert caplog.records[-1].levelname == "WARNING"

        # 5回目: INFO
        pytilpack.logging.exception_with_dedup(logger, exc, dedup_count=3, now=now)
        assert caplog.records[-1].levelname == "INFO"


def test_exception_with_dedup_count_str(caplog: pytest.LogCaptureFixture) -> None:
    """exception_with_dedupの個数窓+文字列テスト。"""
    logger = logging.getLogger("test_logger_count_str")
    logger.setLevel(logging.DEBUG)

    now = datetime.datetime(2023, 1, 1, 12, 0, 0)

    with caplog.at_level(logging.INFO):
        # 1回目: WARNING (exc_info なし)
        pytilpack.logging.exception_with_dedup(logger, "timeout", dedup_count=2, now=now)
        assert caplog.records[-1].levelname == "WARNING"
        assert caplog.records[-1].exc_info is None

        # 2回目: INFO
        pytilpack.logging.exception_with_dedup(logger, "timeout", dedup_count=2, now=now)
        assert caplog.records[-1].levelname == "INFO"

        # 3回目: WARNING (count=2 → reset)
        pytilpack.logging.exception_with_dedup(logger, "timeout", dedup_count=2, now=now)
        assert caplog.records[-1].levelname == "WARNING"
        assert caplog.records[-1].exc_info is None


def test_exception_with_dedup_both_windows(caplog: pytest.LogCaptureFixture) -> None:
    """exception_with_dedupの時間窓+個数窓併用テスト。"""
    logger = logging.getLogger("test_logger_both")
    logger.setLevel(logging.DEBUG)

    now = datetime.datetime(2023, 1, 1, 12, 0, 0)
    dedup_window = datetime.timedelta(hours=1)
    exc = ValueError("test error")

    with caplog.at_level(logging.INFO):
        # 1回目: WARNING
        pytilpack.logging.exception_with_dedup(logger, exc, dedup_window=dedup_window, dedup_count=5, now=now)
        assert caplog.records[-1].levelname == "WARNING"

        # 2〜4回目: INFO（時間窓内かつ個数窓内）
        for _ in range(3):
            pytilpack.logging.exception_with_dedup(logger, exc, dedup_window=dedup_window, dedup_count=5, now=now)
            assert caplog.records[-1].levelname == "INFO"

        # 時間窓が先に超過 → WARNING
        now2 = now + datetime.timedelta(hours=2)
        pytilpack.logging.exception_with_dedup(logger, exc, dedup_window=dedup_window, dedup_count=5, now=now2)
        assert caplog.records[-1].levelname == "WARNING"

    caplog.clear()
    pytilpack.logging.clear_exception_history()

    with caplog.at_level(logging.INFO):
        # 1回目: WARNING
        pytilpack.logging.exception_with_dedup(logger, exc, dedup_window=dedup_window, dedup_count=3, now=now)
        assert caplog.records[-1].levelname == "WARNING"

        # 2〜3回目: INFO
        for _ in range(2):
            pytilpack.logging.exception_with_dedup(logger, exc, dedup_window=dedup_window, dedup_count=3, now=now)
            assert caplog.records[-1].levelname == "INFO"

        # 個数窓が先に超過（時間窓内だが count=3 に到達）→ WARNING
        pytilpack.logging.exception_with_dedup(logger, exc, dedup_window=dedup_window, dedup_count=3, now=now)
        assert caplog.records[-1].levelname == "WARNING"


@pytest.mark.asyncio
async def test_capture_context() -> None:
    """capture_contextのテスト。"""
    logger = logging.getLogger("test_capture_context")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(levelname)s] %(message)s")

    captured_content = ""
    async with pytilpack.logging.capture_context(logger, formatter, logging.INFO) as get_value:
        # キャプチャ開始時は空
        assert get_value() == ""

        # ログを出力
        logger.info("テストメッセージ1")
        logger.debug("デバッグメッセージ")  # レベルが低いので出力されない
        logger.warning("テストメッセージ2")

        # キャプチャされた内容を確認
        captured_content = get_value()
        assert "[INFO] テストメッセージ1\n" in captured_content
        assert "[WARNING] テストメッセージ2\n" in captured_content
        assert "デバッグメッセージ" not in captured_content

    # コンテキスト終了後は新しいログはキャプチャされない
    logger.info("コンテキスト外のメッセージ")
    # コンテキスト終了前にキャプチャした内容には、コンテキスト外のメッセージは含まれない
    assert "コンテキスト外のメッセージ" not in captured_content


@pytest.mark.asyncio
async def test_capture_context_multiple_tasks() -> None:
    """複数のタスクでのcapture_contextのテスト。"""
    logger = logging.getLogger("test_capture_context_multi")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(levelname)s] %(message)s")

    async def task1():
        async with pytilpack.logging.capture_context(logger, formatter, logging.INFO) as get_value:
            logger.info("タスク1のメッセージ")
            await asyncio.sleep(0.01)
            logger.warning("タスク1の警告")
            return get_value()

    async def task2():
        async with pytilpack.logging.capture_context(logger, formatter, logging.INFO) as get_value:
            await asyncio.sleep(0.005)
            logger.info("タスク2のメッセージ")
            logger.error("タスク2のエラー")
            return get_value()

    # 並行実行
    result1, result2 = await asyncio.gather(task1(), task2())

    # それぞれのタスクは自分のログのみキャプチャしている
    assert "タスク1のメッセージ" in result1
    assert "タスク1の警告" in result1
    assert "タスク2のメッセージ" not in result1
    assert "タスク2のエラー" not in result1

    assert "タスク2のメッセージ" in result2
    assert "タスク2のエラー" in result2
    assert "タスク1のメッセージ" not in result2
    assert "タスク1の警告" not in result2


@pytest.mark.asyncio
async def test_capture_context_nested() -> None:
    """ネストしたcapture_contextのテスト。"""
    logger = logging.getLogger("test_capture_context_nested")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(levelname)s] %(message)s")

    async with pytilpack.logging.capture_context(logger, formatter, logging.INFO) as outer_get_value:
        logger.info("外側のメッセージ1")

        async with pytilpack.logging.capture_context(logger, formatter, logging.WARNING) as inner_get_value:
            logger.info("内側のメッセージ（INFOレベル）")  # 内側のレベルがWARNINGなので出力されない
            logger.warning("内側のメッセージ（WARNINGレベル）")

            inner_captured = inner_get_value()
            assert "内側のメッセージ（WARNINGレベル）" in inner_captured
            assert "内側のメッセージ（INFOレベル）" not in inner_captured
            assert "外側のメッセージ1" not in inner_captured

        logger.info("外側のメッセージ2")

        outer_captured = outer_get_value()
        assert "外側のメッセージ1" in outer_captured
        assert "外側のメッセージ2" in outer_captured
        # 内側のコンテキストのログは外側のコンテキストIDとは異なるため外側にはキャプチャされない
        assert "内側のメッセージ（WARNINGレベル）" not in outer_captured


@pytest.mark.parametrize(
    "data,max_str_len,max_bytes_len,bytes_to_str,expected",
    [
        # 文字列の省略
        ("short", 100, 100, False, "short"),
        ("a" * 150, 100, 100, False, "a" * 100 + "..."),
        # バイト列の省略
        (b"short", 100, 100, False, b"short"),
        (b"x" * 150, 100, 100, False, b"x" * 100 + b"..."),
        # bytes_to_str=True の場合
        (b"short", 100, 100, True, "short"),
        (b"x" * 150, 100, 100, True, "x" * 100 + "..."),
        # dictの再帰処理
        ({"key": "a" * 150}, 100, 100, False, {"key": "a" * 100 + "..."}),
        ({"k1": "short", "k2": "b" * 150}, 100, 100, False, {"k1": "short", "k2": "b" * 100 + "..."}),
        ({"k1": b"short", "k2": b"x" * 150}, 100, 100, True, {"k1": "short", "k2": "x" * 100 + "..."}),
        # listの再帰処理
        (["short", "a" * 150], 100, 100, False, ["short", "a" * 100 + "..."]),
        ([b"short", b"x" * 150], 100, 100, True, ["short", "x" * 100 + "..."]),
        # tupleの再帰処理
        (("short", "a" * 150), 100, 100, False, ("short", "a" * 100 + "...")),
        ((b"short", b"x" * 150), 100, 100, True, ("short", "x" * 100 + "...")),
        # ネストした構造
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
        # その他の型はそのまま
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
    """truncate_valuesのテスト。"""
    actual = pytilpack.logging.truncate_values(data, max_str_len, max_bytes_len, bytes_to_str)
    assert actual == expected


@pytest.mark.parametrize(
    "obj,indent,truncate,expected",
    [
        # 基本的なJSON化
        ({"key": "value"}, None, False, '{"key":"value"}'),
        ({"key": "値"}, None, False, '{"key":"値"}'),
        # インデント付き
        ({"key": "value"}, 2, False, '{\n  "key": "value"\n}'),
        # truncate=True の場合
        ({"key": "a" * 150}, None, True, '{"key":"' + "a" * 100 + '..."}'),
        ({"key": b"x" * 150}, None, True, '{"key":"' + "x" * 100 + '..."}'),
        # truncate=False の場合
        ({"key": "a" * 150}, None, False, '{"key":"' + "a" * 150 + '"}'),
        # リストとネスト
        ([1, 2, 3], None, False, "[1,2,3]"),
        ({"list": ["a" * 150, "b"]}, None, True, '{"list":["' + "a" * 100 + '...","b"]}'),
        # datetime変換
        ({"dt": datetime.datetime(2023, 1, 1, 12, 0, 0, 123000)}, None, False, '{"dt":"2023-01-01T12:00:00.123"}'),
        ({"date": datetime.date(2023, 1, 1)}, None, False, '{"date":"2023-01-01"}'),
        # pathlib.Path変換
        ({"path": pathlib.Path("/tmp/test")}, None, False, '{"path":"/tmp/test"}'),
    ],
)
def test_jsonify(
    obj: typing.Any,
    indent: int | None,
    truncate: bool,
    expected: str,
) -> None:
    """jsonifyのテスト。"""
    actual = pytilpack.logging.jsonify(obj, indent, truncate)
    assert actual == expected
