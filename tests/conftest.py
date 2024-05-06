"""テストコード用の共通設定。"""

import pathlib

import pytest


@pytest.fixture
def data_dir():
    """テストデータのディレクトリパスを返す。"""
    yield pathlib.Path(__file__).parent / "data"
