"""pytest用のユーティリティ集。"""

import getpass
import logging
import os
import pathlib
import tempfile

import pytest

logger = logging.getLogger(__name__)

# get_tmp_pathが参照する環境変数名。register_basetmpで設定される。
_BASETMP_ENV = "PYTILPACK_PYTEST_BASETMP"


class AssertBlock:
    """大きいデータ (画面のHTML等) をpytestのassertで確認するためのユーティリティ。

    ブロック内でエラーが発生した場合、dataを一時ファイルに書き出し、そのパスを例外メッセージに出力する。

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
        """コンテキストマネージャーのexit。エラーが発生した場合はdataを一時ファイルに書き出し、パスをログと例外メッセージに出力する。"""
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
        """非同期コンテキストマネージャーのexit。エラーが発生した場合はdataを一時ファイルに書き出し、パスをログと例外メッセージに出力する。"""
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


def register_basetmp(tmp_path_factory: pytest.TempPathFactory) -> None:
    """pytestのbasetmpを環境変数に登録する。

    ``get_tmp_path``がシンボリックリンク (``pytest-current``) 経由のフォールバックを
    使わず、pytest本体のbasetmpを直接参照できるようにする。これにより複数の
    pytestプロセスが近接した環境でも``tmp_path``との照合が非決定的にならない。

    本ライブラリを利用するプロジェクトの``tests/conftest.py``にautouseのセッション
    スコープfixtureを定義して呼び出すこと。

    Example:
        ``tests/conftest.py``で以下のように使う::

            import pytest
            import pytilpack.pytest


            @pytest.fixture(autouse=True, scope="session")
            def _pytilpack_basetmp(
                tmp_path_factory: pytest.TempPathFactory,
            ) -> None:
                pytilpack.pytest.register_basetmp(tmp_path_factory)

    """
    os.environ[_BASETMP_ENV] = str(tmp_path_factory.getbasetemp())


def get_tmp_path() -> pathlib.Path:
    """一時ファイルを置けるディレクトリを返す。

    ``tmp_path``/``tmp_path_factory`` fixtureを直接使用することが望ましいが、
    手軽に利用したい場合向けの簡易関数である。

    ``register_basetmp``が呼ばれていれば、pytest本体のbasetmpを直接返す。
    呼ばれていない場合は``pytest-of-<user>/pytest-current``シンボリックリンク
    経由のフォールバックを使う。ただしフォールバック経路は並列/近接した別の
    pytestプロセスがある環境で``tmp_path``と一致しないことがあるため、
    本ライブラリの利用者は``register_basetmp``の利用を推奨する。

    """
    basetmp = os.environ.get(_BASETMP_ENV)
    if basetmp is not None:
        # register_basetmp経由: pytest_xdistではworkerごとのbasetmpが既に個別化されている
        path = pathlib.Path(basetmp)
    else:
        # フォールバック: pytest-currentシンボリックリンクを解決する
        username = getpass.getuser()
        path = pathlib.Path(tempfile.gettempdir()) / f"pytest-of-{username}" / "pytest-current"
        path = path.resolve()
        # pytest-xdist環境ではワーカーごとのサブディレクトリが使われる
        worker_id = os.environ.get("PYTEST_XDIST_WORKER")
        if worker_id is not None:
            path = path / f"popen-{worker_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path
