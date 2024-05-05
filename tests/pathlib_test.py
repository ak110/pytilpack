"""テストコード。"""

import pytilpack.pathlib_


def test_delete_file(tmp_path):
    """delete_file()のテスト。"""
    path = tmp_path / "test.txt"
    path.write_text("test")
    pytilpack.pathlib_.delete_file(path)
    assert not path.exists()


def test_get_size(tmp_path):
    """get_size()のテスト。"""
    (tmp_path / "test").mkdir()
    (tmp_path / "test" / "test.txt").write_text("test")
    assert pytilpack.pathlib_.get_size(tmp_path) == 4
    assert pytilpack.pathlib_.get_size(tmp_path / "not_exist") == 0
