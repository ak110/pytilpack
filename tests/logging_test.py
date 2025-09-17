"""テストコード。"""

import asyncio
import datetime
import logging
import pathlib

import pytest

import pytilpack.logging


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


def test_timer_done(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO), pytilpack.logging.timer("test"):
        pass

    assert caplog.record_tuples == [("pytilpack.logging", logging.INFO, "[test] done in 0 s")]


def test_timer_failed(caplog: pytest.LogCaptureFixture) -> None:
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

    # ログ履歴をクリア
    pytilpack.logging._exception_history.clear()  # pylint: disable=protected-access

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
