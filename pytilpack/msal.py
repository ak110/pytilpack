__lazy_modules__ = [
    "azure.core",
    "azure.core.credentials",
    "binascii",
    "cryptography",
    "cryptography.hazmat.backends",
    "cryptography.hazmat.primitives.hashes",
    "cryptography.x509",
    "datetime",
    "msal",
    "pathlib",
    "threading",
]

import binascii
import datetime as dt
import pathlib
import threading

import azure.core
import azure.core.credentials
import cryptography
import cryptography.hazmat.backends
import cryptography.hazmat.primitives.hashes
import cryptography.x509
import msal


def load_pem_certificate(certificate_path: pathlib.Path | str) -> dict:
    return load_pem_certificate_data(pathlib.Path(certificate_path).read_bytes())


def load_pem_certificate_data(certificate_data: bytes) -> dict:
    cert = cryptography.x509.load_pem_x509_certificate(certificate_data, cryptography.hazmat.backends.default_backend())
    # Azure AD証明書認証ではSHA-1フィンガープリントをthumbprintとして要求する仕様のため、
    # SHA-1を使用する（セキュリティ上の選択ではなくAzure APIの要件）。
    fingerprint = cert.fingerprint(cryptography.hazmat.primitives.hashes.SHA1())
    return {
        "private_key": certificate_data,
        "thumbprint": binascii.hexlify(fingerprint).decode("utf-8"),
    }


class SimpleTokenCredential(azure.core.credentials.TokenCredential):
    def __init__(self, access_token: str, expires_in: int):
        self.access_token = access_token
        self.expires: dt.datetime = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=expires_in)
        self.expires_on: int = int(self.expires.timestamp())

    def get_token(self, *args, **kwargs) -> azure.core.credentials.AccessToken:
        del args, kwargs
        return azure.core.credentials.AccessToken(self.access_token, self.expires_on)


_file_token_cache_lock = threading.Lock()


class FileTokenCache:
    def __init__(self, cache_path: pathlib.Path | str):
        self.cache_path = pathlib.Path(cache_path)
        self.cache = msal.SerializableTokenCache()
        with _file_token_cache_lock:
            if self.cache_path.exists():
                self.cache.deserialize(self.cache_path.read_text("utf-8", errors="replace"))

    def get(self) -> msal.SerializableTokenCache:
        return self.cache

    def save(self) -> None:
        with _file_token_cache_lock:
            if self.cache.has_state_changed:
                self.cache_path.write_text(self.cache.serialize(), "utf-8", errors="replace")
