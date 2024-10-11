"""pytest用のユーティリティ集。"""

import getpass
import pathlib
import tempfile


def tmp_path() -> pathlib.Path:
    """temp_path fixtureの指し示す先の１つ上の階層と思わしきパスを返す。

    (できればちゃんとfixture使った方がいいけど面倒なとき用)

    """
    username = getpass.getuser()
    path = (
        pathlib.Path(tempfile.gettempdir()) / f"pytest-of-{username}" / "pytest-current"
    )
    return path.resolve()


def tmp_file_path(
    tmp_path_: pathlib.Path | None = None, suffix: str = ".txt", prefix: str = "tmp"
) -> pathlib.Path:
    """一時ファイルパスを返す。"""
    if tmp_path_ is None:
        tmp_path_ = tmp_path()
    with tempfile.NamedTemporaryFile(
        suffix=suffix, prefix=prefix, dir=tmp_path_, delete=False
    ) as f:
        return pathlib.Path(f.name)
