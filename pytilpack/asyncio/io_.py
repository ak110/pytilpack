"""非同期I/O関連。"""

import asyncio
import datetime
import logging
import pathlib
import typing

import pytilpack.json
import pytilpack.pathlib

logger = logging.getLogger(__name__)


async def read_json(path: pathlib.Path | str) -> dict[str, typing.Any]:
    """JSONファイルから非同期で読み取る。"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, pytilpack.json.load, path)


async def write_json(
    path: pathlib.Path | str,
    data: dict,
    ensure_ascii: bool = False,
    indent: int | None = None,
    separators: tuple[str, str] | None = None,
    sort_keys: bool = False,
) -> None:
    """JSONファイルに非同期で書き込む。"""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        pytilpack.json.save,
        path,
        data,
        ensure_ascii,
        indent,
        separators,
        sort_keys,
    )


async def read_text(path: pathlib.Path | str, encoding: str = "utf-8", errors: str = "strict") -> str:
    """ファイルからテキストを非同期で読み取る。"""
    path = pathlib.Path(path)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, path.read_text, encoding, errors)


async def write_text(path: pathlib.Path | str, data: str, encoding: str = "utf-8", errors: str = "strict") -> None:
    """ファイルにテキストを非同期で書き込む。"""
    path = pathlib.Path(path)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, path.write_text, data, encoding, errors)


async def append_text(path: pathlib.Path | str, data: str, encoding: str = "utf-8", errors: str = "strict") -> None:
    """ファイルにテキストを非同期で追記する。"""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, pytilpack.pathlib.append_text, path, data, encoding, errors)


async def read_bytes(path: pathlib.Path | str) -> bytes:
    """ファイルからバイトを非同期で読み取る。"""
    path = pathlib.Path(path)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, path.read_bytes)


async def write_bytes(path: pathlib.Path | str, data: bytes) -> None:
    """ファイルにバイトを非同期で書き込む。"""
    path = pathlib.Path(path)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, path.write_bytes, data)


async def append_bytes(path: pathlib.Path | str, data: bytes) -> None:
    """ファイルにバイトを非同期で追記する。"""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, pytilpack.pathlib.append_bytes, path, data)


async def delete_file(path: pathlib.Path | str) -> None:
    """ファイルを非同期で削除する。"""
    path = pathlib.Path(path)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, pytilpack.pathlib.delete_file, path)


async def get_size(path: pathlib.Path | str) -> int:
    """ファイル・ディレクトリのサイズを非同期で取得する。"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, pytilpack.pathlib.get_size, path)


async def delete_empty_dirs(path: str | pathlib.Path, keep_root: bool = True) -> None:
    """指定したパス以下の空ディレクトリを削除する。

    Args:
        path: 対象のパス
        keep_root: Trueの場合、指定したディレクトリ自体は削除しない
    """
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, pytilpack.pathlib.delete_empty_dirs, path, keep_root)


async def sync(src: str | pathlib.Path, dst: str | pathlib.Path, delete: bool = False) -> None:
    """コピー元からコピー先へ同期する。

    Args:
        src: コピー元のパス
        dst: コピー先のパス
        delete: Trueの場合、コピー元に存在しないファイル・ディレクトリをコピー先から削除する
    """
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, pytilpack.pathlib.sync, src, dst, delete)


async def delete_old_files(
    path: str | pathlib.Path,
    before: datetime.datetime,
    delete_empty_dirs: bool = True,  # pylint: disable=redefined-outer-name
    keep_root_empty_dir: bool = True,
) -> None:
    """指定した日時より古いファイルを削除し、空になったディレクトリも削除する。

    Args:
        path: 対象のパス
        before: この日時より前に更新されたファイルを削除
        delete_empty_dirs: Trueの場合、空になったディレクトリを削除
        keep_root_empty_dir: Trueの場合、指定したディレクトリ自体は削除しない
    """
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, pytilpack.pathlib.delete_old_files, path, before, delete_empty_dirs, keep_root_empty_dir)
