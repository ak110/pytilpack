"""テストコード。"""

import pytilpack.flask_login_


def test_import():
    assert pytilpack.flask_login_.is_admin is not None
    assert pytilpack.flask_login_.admin_only is not None
