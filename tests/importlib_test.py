"""テストコード。"""

import logging
import pathlib

import pytest

import pytilpack.importlib


def test_import_all(caplog: pytest.LogCaptureFixture) -> None:
    """import_all()のテスト。"""
    # ログレベルをDEBUGに設定してログをキャプチャ
    with caplog.at_level(logging.DEBUG):
        base_path = pathlib.Path(__file__).parent.parent
        pytilpack.importlib.import_all(base_path / "pytilpack", base_path)

    # モジュールがインポートされていることをログで確認
    log_messages = [record.message for record in caplog.records]
    assert any(message == "Importing module: pytilpack" for message in log_messages)
    assert any(message == "Importing module: pytilpack.importlib" for message in log_messages)
