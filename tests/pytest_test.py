"""テストコード。"""

import pytilpack.pytest_


def test_tmp_path(tmp_path):
    assert pytilpack.pytest_.tmp_path() == tmp_path.parent


def test_tmp_file_path():
    assert pytilpack.pytest_.tmp_file_path().exists()
