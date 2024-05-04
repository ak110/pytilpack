"""テストコード。"""

import pytilpack.flask_


def test_generate_secret_key(tmp_path):
    path = tmp_path / "secret_key"
    assert not path.exists()
    secret_key1 = pytilpack.flask_.generate_secret_key(path)
    assert path.exists()
    secret_key2 = pytilpack.flask_.generate_secret_key(path)
    assert secret_key1 == secret_key2
