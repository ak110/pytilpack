"""pytest用のユーティリティ集。"""

import getpass
import logging
import pathlib
import tempfile

logger = logging.getLogger(__name__)


class AssertBlock:
    """大きいデータ(例えば画面のHTML)をpytestのassertで確認するとき用ユーティリティ。

    ブロック内でエラーが出た時、dataを一時ファイルに書き出して、そのパスを例外メッセージに出力する。

    例::

        def test_something():
            data = ... # 画面のHTMLなどの大きいデータ
            with pytilpack.pytest.AssertBlock(data, ".html"):
                assert "expected string" in data

    """

    def __init__(
        self,
        data: str | bytes,
        suffix: str = ".html",
        encoding: str = "utf-8",
        errors: str = "replace",
        tmp_path: pathlib.Path | None = None,
    ) -> None:
        self.data = data
        self.suffix = suffix
        self.tmp_path = tmp_path
        self.encoding = encoding
        self.errors = errors

    def __enter__(self) -> None:
        """コンテキストマネージャーのenter。"""

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """コンテキストマネージャーのexit。エラーがあったらdataを一時ファイルに書き出してパスをログと例外メッセージに出力する。"""
        del exc_tb  # noqa
        if exc_type is None:
            return
        if exc_type is AssertionError:
            path = create_temp_view(
                tmp_path=self.tmp_path, data=self.data, suffix=self.suffix, encoding=self.encoding, errors=self.errors
            )
            logger.error(f"アサーションエラー: {exc_val}, <{path}>")
            msg = str(exc_val)
            if len(msg) > 24:
                matches = [(i, p) for p in ("' in '", "' in b'") if (i := msg.find(p)) != -1]
                if matches:
                    i, p = min(matches)
                    msg = msg[: i + len(p)] + "..."
                else:
                    msg = msg[:24] + "..."
            raise AssertionError(f"{msg}, <{path}>") from exc_val

    async def __aenter__(self) -> None:
        """非同期コンテキストマネージャーのenter。"""
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """非同期コンテキストマネージャーのexit。エラーがあったらdataを一時ファイルに書き出してパスをログと例外メッセージに出力する。"""
        self.__exit__(exc_type, exc_val, exc_tb)


def create_temp_view(
    tmp_path: pathlib.Path | None,
    data: str | bytes,
    suffix: str,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> pathlib.Path:
    """データの確認用に一時ファイルを作成する。"""
    output_path = tmp_file_path(tmp_path=tmp_path, suffix=suffix)
    if isinstance(data, str):
        data = data.encode(encoding=encoding, errors=errors)
    else:
        assert isinstance(data, bytes)
    output_path.write_bytes(data)
    logger.info(f"view: {output_path}")
    return output_path


def tmp_file_path(tmp_path: pathlib.Path | None = None, suffix: str = ".txt", prefix: str = "tmp") -> pathlib.Path:
    """一時ファイルパスを返す。"""
    if tmp_path is None:
        tmp_path = get_tmp_path()
    with tempfile.NamedTemporaryFile(suffix=suffix, prefix=prefix, dir=tmp_path, delete=False) as f:
        return pathlib.Path(f.name)


def get_tmp_path() -> pathlib.Path:
    """temp_path fixtureの指し示す先の１つ上の階層と思わしきパスを返す。

    (できればちゃんとfixture使った方がいいけど面倒なとき用)

    """
    username = getpass.getuser()
    path = pathlib.Path(tempfile.gettempdir()) / f"pytest-of-{username}" / "pytest-current"
    return path.resolve()
