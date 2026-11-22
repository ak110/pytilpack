import logging
import sys

import pytest

import pytilpack.tqdm


def test_tqdm_stream_handler(capsys):
    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)
    handler = pytilpack.tqdm.TqdmStreamHandler()
    logger.addHandler(handler)
    try:
        handler.setFormatter(logging.Formatter("[%(levelname)-5s] %(message)s"))

        logger.debug("debug")
        logger.info("info")
        logger.warning("warning")
        logger.error("error")
        logger.critical("critical")

        assert capsys.readouterr().err == "[INFO ] info\n[WARNING] warning\n[ERROR] error\n[CRITICAL] critical\n"
    finally:
        logger.removeHandler(handler)
        handler.close()


@pytest.mark.parametrize(
    "flags,during,after",
    [
        ({}, ("", ""), ("stdout\n", "stderr\n")),
        ({"capture_stdout": True, "capture_stderr": False}, ("", "stderr\n"), ("stdout\n", "")),
    ],
)
def test_capture(capsys, flags, during, after):
    with pytilpack.tqdm.capture(**flags):
        print("stderr", file=sys.stderr)
        print("stdout")
        assert capsys.readouterr() == during
    assert capsys.readouterr() == after
