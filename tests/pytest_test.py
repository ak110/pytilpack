"""テストコード。"""

import pathlib

import pytilpack.pytest_


def test_tmp_path(tmp_path: pathlib.Path) -> None:
    assert pytilpack.pytest_.tmp_path() == tmp_path.parent


def test_tmp_file_path() -> None:
    assert pytilpack.pytest_.tmp_file_path().exists()
