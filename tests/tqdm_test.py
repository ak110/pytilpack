"""テストコード。"""

import logging

import pytilpack.tqdm_


def test_tqdm_stream_handler(capsys):
    """TqdmStreamHandlerのテスト。"""
    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)
    logger.addHandler(pytilpack.tqdm_.TqdmStreamHandler())
    try:
        logger.handlers[-1].setFormatter(
            logging.Formatter("[%(levelname)s] %(message)s")
        )

        logger.debug("debug")
        logger.info("info")
        logger.warning("warning")
        logger.error("error")
        logger.critical("critical")

        assert (
            capsys.readouterr().err
            == "[INFO] info\n[WARNING] warning\n[ERROR] error\n[CRITICAL] critical\n"
        )
    finally:
        logger.removeHandler(pytilpack.tqdm_.TqdmStreamHandler())
