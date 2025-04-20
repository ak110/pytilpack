"""テストコード。"""

import pathlib

import pytilpack.secrets_


def test_generate_secret_key(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "secret_key"
    assert not path.exists()
    secret_key1 = pytilpack.secrets_.generate_secret_key(path)
    assert path.exists()
    secret_key2 = pytilpack.secrets_.generate_secret_key(path)
    assert secret_key1 == secret_key2
