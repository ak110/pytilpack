"""テストコード。"""

import logging
import pathlib

import pytest

import pytilpack.logging_


def test_logging(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture) -> None:
    logger = logging.getLogger(__name__)
    try:
        logger.setLevel(logging.DEBUG)
        logger.addHandler(pytilpack.logging_.stream_handler())
        logger.addHandler(pytilpack.logging_.file_handler(tmp_path / "test.log"))

        logger.debug("debug")
        logger.info("info")
        logger.warning("warning")

        assert (tmp_path / "test.log").read_text(
            encoding="utf-8"
        ) == "[DEBUG] debug\n[INFO ] info\n[WARNING] warning\n"
        assert capsys.readouterr().err == "[INFO ] info\n[WARNING] warning\n"
    finally:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)


def test_timer_done(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        with pytilpack.logging_.timer("test"):
            pass

    assert caplog.record_tuples == [
        ("pytilpack.logging_", logging.INFO, "[test] done in 0 s")
    ]


def test_timer_failed(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        try:
            with pytilpack.logging_.timer("test"):
                raise ValueError()
        except ValueError:
            pass

    assert caplog.record_tuples == [
        ("pytilpack.logging_", logging.WARNING, "[test] failed in 0 s")
    ]
