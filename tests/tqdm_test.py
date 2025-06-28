"""テストコード。"""

import logging
import sys

import pytilpack.tqdm


def test_tqdm_stream_handler(capsys):
    """TqdmStreamHandlerのテスト。"""
    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)
    logger.addHandler(pytilpack.tqdm.TqdmStreamHandler())
    try:
        logger.handlers[-1].setFormatter(logging.Formatter("[%(levelname)-5s] %(message)s"))

        logger.debug("debug")
        logger.info("info")
        logger.warning("warning")
        logger.error("error")
        logger.critical("critical")

        assert capsys.readouterr().err == "[INFO ] info\n[WARNING] warning\n[ERROR] error\n[CRITICAL] critical\n"
    finally:
        logger.removeHandler(pytilpack.tqdm.TqdmStreamHandler())


def test_capture(capsys):
    """captureのテスト。"""
    with pytilpack.tqdm.capture():
        print("stderr", file=sys.stderr)
        print("stdout")
    assert capsys.readouterr() == ("stdout\n", "stderr\n")
