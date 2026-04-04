"""テストコード。"""

import base64

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
    """TimestampSignerの署名・検証・purpose分離・有効期限・改ざん検知のテスト。"""
    # ラウンドトリップ: str / bytes / dict
    signer = pytilpack.crypto.TimestampSigner("my-key")

    token_str = signer.sign("hello world")
    assert signer.unsign(token_str) == "hello world"

    token_bytes = signer.sign(b"\x00\x01\x02\xff")
    assert signer.unsign(token_bytes) == b"\x00\x01\x02\xff"

    data = {"key": "value", "number": 42, "日本語": "テスト"}
    token_dict = signer.sign(data)
    assert signer.unsign(token_dict) == data

    # purpose分離: 異なるpurposeでは検証失敗
    signer_a = pytilpack.crypto.TimestampSigner("same-key", purpose="a")
    signer_b = pytilpack.crypto.TimestampSigner("same-key", purpose="b")

    token = signer_a.sign("data")
    assert signer_a.unsign(token) == "data"
    with pytest.raises(ValueError):
        signer_b.unsign(token)

    # 有効期限: _get_timeで時刻を注入してテスト
    current_time = 1000.0
    signer_timed = pytilpack.crypto.TimestampSigner("key", get_time=lambda: current_time)
    token = signer_timed.sign("data")

    current_time = 1005.0  # 5秒経過: 期限内
    assert signer_timed.unsign(token, max_age=10.0) == "data"

    current_time = 1060.0  # 60秒経過: 期限切れ
    with pytest.raises(ValueError, match="期限切れ"):
        signer_timed.unsign(token, max_age=10.0)

    # 改ざん検知: トークンのバイト列を直接改ざん
    token = signer.sign("secret data")
    raw = base64.urlsafe_b64decode(token + "==")
    tampered_raw = raw[:10] + bytes([raw[10] ^ 0xFF]) + raw[11:]
    tampered = base64.urlsafe_b64encode(tampered_raw).rstrip(b"=").decode()
    with pytest.raises(ValueError, match="署名が一致しません"):
        signer.unsign(tampered)
