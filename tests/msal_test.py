import datetime as dt
import hashlib
import json
import pathlib
import types

import azure.core.credentials
import cryptography
import cryptography.hazmat.primitives.asymmetric.ed25519
import cryptography.hazmat.primitives.serialization
import cryptography.x509
import cryptography.x509.oid
import pytest

import pytilpack.msal


def test_load_pem_certificate(tmp_path: pathlib.Path) -> None:
    cert_path = tmp_path / "test.pem"

    private_key = cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    subject = issuer = cryptography.x509.Name(
        [cryptography.x509.NameAttribute(cryptography.x509.oid.NameOID.COMMON_NAME, "localhost")]
    )
    cert = (
        cryptography.x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(1)
        .not_valid_before(dt.datetime(2024, 1, 1, tzinfo=dt.UTC))
        .not_valid_after(dt.datetime(2030, 1, 1, tzinfo=dt.UTC))
        .sign(private_key, None)
    )
    cert_pem = cert.public_bytes(cryptography.hazmat.primitives.serialization.Encoding.PEM)
    key_pem = private_key.private_bytes(
        encoding=cryptography.hazmat.primitives.serialization.Encoding.PEM,
        format=cryptography.hazmat.primitives.serialization.PrivateFormat.PKCS8,
        encryption_algorithm=cryptography.hazmat.primitives.serialization.NoEncryption(),
    )
    cert_path.write_bytes(cert_pem + key_pem)

    result = pytilpack.msal.load_pem_certificate(cert_path)
    der = cert.public_bytes(cryptography.hazmat.primitives.serialization.Encoding.DER)
    assert result == {"private_key": cert_pem + key_pem, "thumbprint": hashlib.sha1(der, usedforsecurity=False).hexdigest()}


class _FixedDatetime(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls.fromtimestamp(100_000, tz)


@pytest.mark.parametrize("access_token,expires_in", [("test_token", 3600), ("another_token", 7200)])
def test_simple_token_credential(access_token: str, expires_in: int, monkeypatch: pytest.MonkeyPatch) -> None:
    clock = types.SimpleNamespace(datetime=_FixedDatetime, UTC=dt.UTC, timedelta=dt.timedelta)
    monkeypatch.setattr(pytilpack.msal, "dt", clock)
    cred = pytilpack.msal.SimpleTokenCredential(access_token, expires_in)
    assert isinstance(cred, azure.core.credentials.TokenCredential)

    token = cred.get_token("scope")
    assert token.token == access_token
    assert isinstance(token.expires_on, int)
    assert token.expires_on == 100_000 + expires_in


def test_file_token_cache(tmp_path: pathlib.Path) -> None:
    cache_path = tmp_path / "token_cache.json"
    cache = pytilpack.msal.FileTokenCache(cache_path)
    assert not cache_path.exists()
    cache.save()
    assert not cache_path.exists()

    test_data = {"AppMetadata": {"appmetadata--": {"client_id": None, "environment": None}}}
    cache.get().add(test_data)
    assert cache.get().has_state_changed
    cache.save()
    assert json.loads(cache_path.read_text(encoding="utf-8")) == test_data
    assert not cache.get().has_state_changed

    new_cache = pytilpack.msal.FileTokenCache(cache_path)
    assert not new_cache.get().has_state_changed
    assert json.loads(new_cache.get().serialize()) == test_data
