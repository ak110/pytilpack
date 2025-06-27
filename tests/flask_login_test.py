"""テストコード。"""

import pytilpack.flask_login


def test_import():
    assert pytilpack.flask_login.is_admin is not None
    assert pytilpack.flask_login.admin_only is not None
