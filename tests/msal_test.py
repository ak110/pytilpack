"""MSALユーティリティのテスト。"""

import datetime
import pathlib

import azure.core.credentials
import cryptography
import cryptography.hazmat.primitives.asymmetric.rsa
import cryptography.hazmat.primitives.hashes
import cryptography.hazmat.primitives.serialization
import cryptography.x509
import cryptography.x509.oid
import pytest

import pytilpack.msal


def test_load_pem_certificate(tmp_path: pathlib.Path) -> None:
    """load_pem_certificate()のテスト。"""
    cert_path = tmp_path / "test.pem"

    # テスト用の自己署名証明書を作成
    private_key = cryptography.hazmat.primitives.asymmetric.rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = cryptography.x509.Name(
        [cryptography.x509.NameAttribute(cryptography.x509.oid.NameOID.COMMON_NAME, "localhost")]
    )
    cert = (
        cryptography.x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(cryptography.x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.UTC))
        .not_valid_after(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1))
        .sign(private_key, cryptography.hazmat.primitives.hashes.SHA256())
    )
    cert_pem = cert.public_bytes(cryptography.hazmat.primitives.serialization.Encoding.PEM)
    key_pem = private_key.private_bytes(
        encoding=cryptography.hazmat.primitives.serialization.Encoding.PEM,
        format=cryptography.hazmat.primitives.serialization.PrivateFormat.PKCS8,
        encryption_algorithm=cryptography.hazmat.primitives.serialization.NoEncryption(),
    )
    cert_path.write_bytes(cert_pem + key_pem)

    # load_pem_certificateのテスト
    result = pytilpack.msal.load_pem_certificate(cert_path)
    assert isinstance(result, dict)
    assert "private_key" in result
    assert "thumbprint" in result
    assert len(result["thumbprint"]) == 40  # SHA1ハッシュは40文字の16進数
    assert isinstance(result["private_key"], bytes)


@pytest.mark.parametrize("access_token,expires_in", [("test_token", 3600), ("another_token", 7200)])
def test_simple_token_credential(access_token: str, expires_in: int) -> None:
    """SimpleTokenCredentialのテスト。"""
    cred = pytilpack.msal.SimpleTokenCredential(access_token, expires_in)
    assert isinstance(cred, azure.core.credentials.TokenCredential)

    token = cred.get_token("scope")
    assert token.token == access_token
    assert isinstance(token.expires_on, int)
    # トークンの有効期限が現在時刻から指定された秒数後に設定されていることを確認
    now = datetime.datetime.now(datetime.UTC).timestamp()
    assert token.expires_on == pytest.approx(int(now) + expires_in, abs=1)


def test_file_token_cache(tmp_path: pathlib.Path) -> None:
    """FileTokenCacheのテスト。"""
    cache_path = tmp_path / "token_cache.json"
    cache = pytilpack.msal.FileTokenCache(cache_path)
    assert not cache_path.exists()  # キャッシュファイルはまだ存在しない

    # キャッシュデータを追加して保存
    test_data = {"AppMetadata": {"appmetadata--": {"client_id": None, "environment": None}}}
    cache.get().add(test_data)
    assert cache.get().has_state_changed
    cache.save()
    assert cache_path.exists()
    assert not cache.get().has_state_changed

    # 保存したキャッシュを読み込み
    new_cache = pytilpack.msal.FileTokenCache(cache_path)
    assert not new_cache.get().has_state_changed
    assert cache.get().serialize() == new_cache.get().serialize()
