from __future__ import annotations

__lazy_modules__ = ["getpass", "logging", "os", "pathlib", "tempfile", "typing"]

import getpass
import logging
import os
import pathlib
import tempfile
import typing

if typing.TYPE_CHECKING:
    import pytest  # noqa: TID254  # 型チェック専用で実行時に読み込まれないため列挙しない

logger = logging.getLogger(__name__)

# get_tmp_pathが参照する環境変数名。register_basetmpで設定される。
_BASETMP_ENV = "PYTILPACK_PYTEST_BASETMP"


class AssertBlock:
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
        pass

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        del exc_tb  # noqa
        if exc_type is None:
            return
        if exc_type is AssertionError:
            path = create_temp_view(
                tmp_path=self.tmp_path, data=self.data, suffix=self.suffix, encoding=self.encoding, errors=self.errors
            )
            logger.error(f"アサーションエラー: {exc_val}, <{path}>。保存したファイルを開いて応答の内容を確かめる")
            msg = str(exc_val)
            if len(msg) > 24:
                matches = [(i, p) for p in ("' in '", "' in b'") if (i := msg.find(p)) != -1]
                if matches:
                    i, p = min(matches)
                    msg = msg[: i + len(p)] + "..."
                else:
                    msg = msg[:24] + "..."
            raise AssertionError(f"{msg}, <{path}> (open the saved file to inspect the response)") from exc_val

    async def __aenter__(self) -> None:
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.__exit__(exc_type, exc_val, exc_tb)


def create_temp_view(
    tmp_path: pathlib.Path | None,
    data: str | bytes,
    suffix: str,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> pathlib.Path:
    output_path = tmp_file_path(tmp_path=tmp_path, suffix=suffix)
    if isinstance(data, str):
        data = data.encode(encoding=encoding, errors=errors)
    else:
        assert isinstance(data, bytes)
    output_path.write_bytes(data)
    logger.info(f"view: {output_path}")
    return output_path


def tmp_file_path(tmp_path: pathlib.Path | None = None, suffix: str = ".txt", prefix: str = "tmp") -> pathlib.Path:
    if tmp_path is None:
        tmp_path = get_tmp_path()
    with tempfile.NamedTemporaryFile(suffix=suffix, prefix=prefix, dir=tmp_path, delete=False) as f:
        return pathlib.Path(f.name)


def register_basetmp(tmp_path_factory: pytest.TempPathFactory) -> None:
    os.environ[_BASETMP_ENV] = str(tmp_path_factory.getbasetemp())


def get_tmp_path() -> pathlib.Path:
    basetmp = os.environ.get(_BASETMP_ENV)
    if basetmp is not None:
        path = pathlib.Path(basetmp)
    else:
        username = getpass.getuser()
        path = pathlib.Path(tempfile.gettempdir()) / f"pytest-of-{username}" / "pytest-current"
        path = path.resolve()
        worker_id = os.environ.get("PYTEST_XDIST_WORKER")
        if worker_id is not None:
            path = path / f"popen-{worker_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path
