"""pytest用のユーティリティ集。"""

import getpass
import logging
import pathlib
import tempfile

logger = logging.getLogger(__name__)


def tmp_path() -> pathlib.Path:
    """temp_path fixtureの指し示す先の１つ上の階層と思わしきパスを返す。

    (できればちゃんとfixture使った方がいいけど面倒なとき用)

    """
    username = getpass.getuser()
    path = pathlib.Path(tempfile.gettempdir()) / f"pytest-of-{username}" / "pytest-current"
    return path.resolve()


def tmp_file_path(tmp_path_: pathlib.Path | None = None, suffix: str = ".txt", prefix: str = "tmp") -> pathlib.Path:
    """一時ファイルパスを返す。"""
    if tmp_path_ is None:
        tmp_path_ = tmp_path()
    with tempfile.NamedTemporaryFile(suffix=suffix, prefix=prefix, dir=tmp_path_, delete=False) as f:
        return pathlib.Path(f.name)


def create_temp_view(
    tmp_path_: pathlib.Path | None,
    data: str | bytes,
    suffix: str,
    encoding: str = "utf-8",
) -> pathlib.Path:
    """データの確認用に一時ファイルを作成する。"""
    output_path = tmp_file_path(tmp_path_, suffix=suffix)
    if isinstance(data, str):
        data = data.encode(encoding)
    elif not isinstance(data, bytes):
        raise TypeError(f"data must be str or bytes, not {type(data)}")
    output_path.write_bytes(data)
    logger.info(f"view: {output_path}")
    return output_path
