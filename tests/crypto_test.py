"""テストコード。"""

import base64
import unittest.mock

import pytest

import pytilpack.crypto


def test_hmac_sign_verify() -> None:
    """HMAC署名・検証のテスト。"""
    key = "test-secret-key"

    # strデータの署名・検証
    sig = pytilpack.crypto.hmac_sign("hello", key)
    assert pytilpack.crypto.hmac_verify("hello", sig, key)

    # bytesデータの署名・検証
    sig_bytes = pytilpack.crypto.hmac_sign(b"hello bytes", key)
    assert pytilpack.crypto.hmac_verify(b"hello bytes", sig_bytes, key)

    # 改ざんされたデータは検証失敗
    assert not pytilpack.crypto.hmac_verify("tampered", sig, key)

    # 異なる鍵では検証失敗
    assert not pytilpack.crypto.hmac_verify("hello", sig, "wrong-key")


def test_timestamp_signer() -> None:
    """TimestampSignerの署名・検証ラウンドトリップテスト。"""
    signer = pytilpack.crypto.TimestampSigner("my-key")

    # str
    token_str = signer.sign("hello world")
    assert signer.unsign(token_str) == "hello world"

    # bytes
    token_bytes = signer.sign(b"\x00\x01\x02\xff")
    assert signer.unsign(token_bytes) == b"\x00\x01\x02\xff"

    # dict
    data = {"key": "value", "number": 42, "日本語": "テスト"}
    token_dict = signer.sign(data)
    assert signer.unsign(token_dict) == data


def test_timestamp_signer_purpose() -> None:
    """purpose分離のテスト。"""
    signer_a = pytilpack.crypto.TimestampSigner("same-key", purpose="a")
    signer_b = pytilpack.crypto.TimestampSigner("same-key", purpose="b")

    token = signer_a.sign("data")
    # 同じpurposeでは検証成功
    assert signer_a.unsign(token) == "data"
    # 異なるpurposeでは検証失敗
    with pytest.raises(ValueError):
        signer_b.unsign(token)


def test_timestamp_signer_expired() -> None:
    """有効期限切れのテスト。"""
    signer = pytilpack.crypto.TimestampSigner("key")

    # 現在時刻でトークン生成
    with unittest.mock.patch("pytilpack.crypto.time") as mock_time:
        mock_time.time.return_value = 1000.0
        token = signer.sign("data")

    # 期限内なら検証成功
    with unittest.mock.patch("pytilpack.crypto.time") as mock_time:
        mock_time.time.return_value = 1005.0
        assert signer.unsign(token, max_age=10.0) == "data"

    # 期限切れなら検証失敗
    with unittest.mock.patch("pytilpack.crypto.time") as mock_time:
        mock_time.time.return_value = 1060.0
        with pytest.raises(ValueError, match="期限切れ"):
            signer.unsign(token, max_age=10.0)


def test_timestamp_signer_tampered() -> None:
    """改ざん検知のテスト。"""
    signer = pytilpack.crypto.TimestampSigner("key")
    token = signer.sign("secret data")

    # トークンのバイト列を直接改ざん（ペイロード部分を変更）
    raw = base64.urlsafe_b64decode(token + "==")
    tampered_raw = raw[:10] + bytes([raw[10] ^ 0xFF]) + raw[11:]
    tampered = base64.urlsafe_b64encode(tampered_raw).rstrip(b"=").decode()
    with pytest.raises(ValueError, match="署名が一致しません"):
        signer.unsign(tampered)
