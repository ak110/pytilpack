"""テストコード。"""

import pathlib

import pytilpack.pytest


def test_tmp_path(tmp_path: pathlib.Path) -> None:
    assert pytilpack.pytest.tmp_path() == tmp_path.parent


def test_tmp_file_path() -> None:
    assert pytilpack.pytest.tmp_file_path().exists()
