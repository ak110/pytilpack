"""テストコード。"""

import os
import pathlib
import unittest.mock

import pytest

import pytilpack.secrets_


def test_generate_secret_key(tmp_path: pathlib.Path) -> None:
    """generate_secret_keyの基本テスト。"""
    path = tmp_path / "secret_key"
    assert not path.exists()
    secret_key1 = pytilpack.secrets_.generate_secret_key(path)
    assert path.exists()
    secret_key2 = pytilpack.secrets_.generate_secret_key(path)
    assert secret_key1 == secret_key2


def test_generate_secret_key_permissions(tmp_path: pathlib.Path) -> None:
    """ファイルパーミッションのテスト。"""
    path = tmp_path / "secret_key"
    pytilpack.secrets_.generate_secret_key(path)
    assert oct(os.stat(path).st_mode)[-3:] == "600"


@unittest.mock.patch("pytilpack.secrets_.secrets.token_bytes")
def test_generate_secret_key_retry(
    mock_token_bytes: unittest.mock.MagicMock, tmp_path: pathlib.Path
) -> None:
    """リトライのテスト。"""
    path = tmp_path / "secret_key"

    # 1回目と2回目は失敗、3回目は成功
    mock_token_bytes.side_effect = [
        IOError("エラー1"),
        IOError("エラー2"),
        b"secret_bytes",
    ]

    result = pytilpack.secrets_.generate_secret_key(path)
    assert result == b"secret_bytes"
    assert mock_token_bytes.call_count == 3


@unittest.mock.patch("pytilpack.secrets_.secrets.token_bytes")
def test_generate_secret_key_retry_exhausted(
    mock_token_bytes: unittest.mock.MagicMock, tmp_path: pathlib.Path
) -> None:
    """リトライ上限のテスト。"""
    path = tmp_path / "secret_key"

    # 全てのリトライで失敗
    mock_token_bytes.side_effect = IOError("常にエラー")

    with pytest.raises(IOError, match="常にエラー"):
        pytilpack.secrets_.generate_secret_key(path)
