"""MSAL関連のユーティリティなど。"""

import binascii
import datetime
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
    """PEM形式の証明書データを読み込み、秘密鍵と指紋を返す。"""
    return load_pem_certificate_data(pathlib.Path(certificate_path).read_bytes())


def load_pem_certificate_data(certificate_data: bytes) -> dict:
    """PEM形式の証明書データを読み込み、秘密鍵と指紋を返す。"""
    cert = cryptography.x509.load_pem_x509_certificate(certificate_data, cryptography.hazmat.backends.default_backend())
    fingerprint = cert.fingerprint(cryptography.hazmat.primitives.hashes.SHA1())
    return {
        "private_key": certificate_data,
        "thumbprint": binascii.hexlify(fingerprint).decode("utf-8"),
    }


class SimpleTokenCredential(azure.core.credentials.TokenCredential):
    """トークンクラス。"""

    def __init__(self, access_token: str, expires_in: int):
        self.access_token = access_token
        self.expires: datetime.datetime = datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=expires_in)
        self.expires_on: int = int(self.expires.timestamp())

    def get_token(self, *args, **kwargs) -> azure.core.credentials.AccessToken:
        del args, kwargs
        return azure.core.credentials.AccessToken(self.access_token, self.expires_on)


_file_token_cache_lock = threading.Lock()
"""FileTokenCache用のロック。"""


class FileTokenCache:
    """MSALのトークンキャッシュ。

    使用例::
        ```python
        token_cache = pytilpack.msal_.FileTokenCache("path/to/cache.json")
        client_app = msal.ConfidentialClientApplication(
            client_id="your_client_id",
            client_credential="your_client_secret",
            token_cache=token_cache.get(),
        )
        ...
        token_cache.save()
        ```

    """

    def __init__(self, cache_path: pathlib.Path | str):
        self.cache_path = pathlib.Path(cache_path)
        self.cache = msal.SerializableTokenCache()
        with _file_token_cache_lock:
            if self.cache_path.exists():
                self.cache.deserialize(self.cache_path.read_text("utf-8", errors="replace"))

    def get(self) -> msal.SerializableTokenCache:
        """キャッシュを取得する。"""
        return self.cache

    def save(self) -> None:
        """キャッシュをファイルに保存する。"""
        with _file_token_cache_lock:
            if self.cache.has_state_changed:
                self.cache_path.write_text(self.cache.serialize(), "utf-8", errors="replace")
