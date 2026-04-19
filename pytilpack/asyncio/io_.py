"""非同期I/O関連。"""

import asyncio
import datetime
import logging
import pathlib
import shutil
import typing

import pytilpack.io
import pytilpack.json
import pytilpack.jsonc
import pytilpack.pathlib

# yaml / pytilpack.yaml は pyyaml extras に依存するため、以降の YAML 系
# 関数内で遅延 import する。pytilpack.asyncio 自体はベース依存のみで動作
# させたい (pytilpack.sqlalchemy 等が pytilpack.asyncio を import する経路で
# pyyaml 不在時に壊れていた)。

logger = logging.getLogger(__name__)


async def read_json(
    path: pytilpack.io.PathOrIO,
    encoding: str = "utf-8",
    errors: str = "replace",
    strict: bool = False,
    **kwargs,
) -> typing.Any:
    """JSONファイルから非同期で読み取る。"""
    return await asyncio.to_thread(
        pytilpack.json.load,
        path,
        encoding,
        errors,
        strict,
        **kwargs,
    )


async def write_json(
    path: pytilpack.io.PathOrIO,
    data: typing.Any,
    ensure_ascii: bool = False,
    indent: int | str | None = None,
    separators: tuple[str, str] | None = None,
    sort_keys: bool = False,
    default: typing.Callable[[typing.Any], typing.Any] = pytilpack.json.converter,
    encoding: str = "utf-8",
    **kwargs,
) -> None:
    """JSONファイルに非同期で書き込む。"""
    await asyncio.to_thread(
        pytilpack.json.save,
        path,
        data,
        ensure_ascii,
        indent,
        separators,
        sort_keys,
        default,
        encoding,
        **kwargs,
    )


async def read_jsonc(
    path: pytilpack.io.PathOrIO,
    encoding: str = "utf-8",
    errors: str = "replace",
    strict: bool = False,
    **kwargs,
) -> typing.Any:
    """JSONCファイルから非同期で読み取る。"""
    return await asyncio.to_thread(
        pytilpack.jsonc.load,
        path,
        encoding,
        errors,
        strict,
        **kwargs,
    )


async def read_yaml(
    path: pytilpack.io.PathOrIO,
    encoding: str = "utf-8",
    errors: str = "replace",
    strict: bool = False,
    Loader: typing.Any = None,
) -> typing.Any:
    """YAMLファイルから非同期で読み取る。"""
    import yaml  # pylint: disable=import-outside-toplevel

    import pytilpack.yaml  # pylint: disable=import-outside-toplevel,redefined-outer-name

    if Loader is None:
        Loader = yaml.SafeLoader
    return await asyncio.to_thread(
        pytilpack.yaml.load,
        path,
        encoding,
        errors,
        strict,
        Loader,
    )


async def read_yaml_all(
    path: pytilpack.io.PathOrIO,
    encoding: str = "utf-8",
    errors: str = "replace",
    strict: bool = False,
    Loader: typing.Any = None,
) -> list[typing.Any]:
    """YAMLファイルから非同期で読み取る。"""
    import yaml  # pylint: disable=import-outside-toplevel

    import pytilpack.yaml  # pylint: disable=import-outside-toplevel,redefined-outer-name

    if Loader is None:
        Loader = yaml.SafeLoader
    return await asyncio.to_thread(
        pytilpack.yaml.load_all,
        path,
        encoding,
        errors,
        strict,
        Loader,
    )


async def write_yaml(
    path: pytilpack.io.PathOrIO,
    data: typing.Any,
    allow_unicode: bool | None = True,
    width: int = 99,
    default_style: str | None = None,
    default_flow_style: bool | None = False,
    sort_keys: bool = False,
    Dumper: typing.Any = None,
    encoding: str = "utf-8",
    **kwargs,
) -> None:
    """YAMLファイルに非同期で書き込む。"""
    import pytilpack.yaml  # pylint: disable=import-outside-toplevel,redefined-outer-name

    if Dumper is None:
        Dumper = pytilpack.yaml.CustomDumper
    await asyncio.to_thread(
        pytilpack.yaml.save,
        path,
        data,
        allow_unicode,
        width,
        default_style,
        default_flow_style,
        sort_keys,
        Dumper,
        encoding,
        **kwargs,
    )


async def write_yaml_all(
    path: pytilpack.io.PathOrIO,
    data: list[typing.Any],
    allow_unicode: bool | None = True,
    width: int = 99,
    default_style: str | None = None,
    default_flow_style: bool | None = False,
    sort_keys: bool = False,
    Dumper: typing.Any = None,
    encoding: str = "utf-8",
    **kwargs,
) -> None:
    """YAMLファイルに非同期で書き込む。"""
    import pytilpack.yaml  # pylint: disable=import-outside-toplevel,redefined-outer-name

    if Dumper is None:
        Dumper = pytilpack.yaml.CustomDumper
    await asyncio.to_thread(
        pytilpack.yaml.save_all,
        path,
        data,
        allow_unicode,
        width,
        default_style,
        default_flow_style,
        sort_keys,
        Dumper,
        encoding,
        **kwargs,
    )


async def read_text(path: pathlib.Path | str, encoding: str = "utf-8", errors: str = "strict") -> str:
    """ファイルからテキストを非同期で読み取る。"""
    path = pathlib.Path(path)
    return await asyncio.to_thread(path.read_text, encoding, errors)


async def write_text(path: pathlib.Path | str, data: str, encoding: str = "utf-8", errors: str = "strict") -> None:
    """ファイルにテキストを非同期で書き込む。"""
    path = pathlib.Path(path)
    await asyncio.to_thread(path.write_text, data, encoding, errors)


async def append_text(path: pathlib.Path | str, data: str, encoding: str = "utf-8", errors: str = "strict") -> None:
    """ファイルにテキストを非同期で追記する。"""
    await asyncio.to_thread(pytilpack.pathlib.append_text, path, data, encoding, errors)


async def read_bytes(path: pathlib.Path | str) -> bytes:
    """ファイルからバイトを非同期で読み取る。"""
    path = pathlib.Path(path)
    return await asyncio.to_thread(path.read_bytes)


async def write_bytes(path: pathlib.Path | str, data: bytes) -> None:
    """ファイルにバイトを非同期で書き込む。"""
    path = pathlib.Path(path)
    await asyncio.to_thread(path.write_bytes, data)


async def append_bytes(path: pathlib.Path | str, data: bytes) -> None:
    """ファイルにバイトを非同期で追記する。"""
    await asyncio.to_thread(pytilpack.pathlib.append_bytes, path, data)


async def copy2(src: pathlib.Path | str, dst: pathlib.Path | str) -> None:
    """ファイルを非同期でメタデータごとコピーする。"""
    await asyncio.to_thread(shutil.copy2, src, dst)


async def copytree(
    src: pathlib.Path | str,
    dst: pathlib.Path | str,
    dirs_exist_ok: bool = False,
) -> None:
    """ディレクトリツリーを非同期で再帰的にコピーする。"""
    await asyncio.to_thread(shutil.copytree, src, dst, dirs_exist_ok=dirs_exist_ok)


async def move(src: pathlib.Path | str, dst: pathlib.Path | str) -> None:
    """ファイルまたはディレクトリを非同期で移動する。"""
    await asyncio.to_thread(shutil.move, src, dst)


async def delete_file(path: pathlib.Path | str) -> None:
    """ファイルを非同期で削除する。"""
    path = pathlib.Path(path)
    await asyncio.to_thread(pytilpack.pathlib.delete_file, path)


async def rmtree(path: pathlib.Path | str, ignore_errors: bool = False) -> None:
    """ディレクトリを非同期で再帰的に削除する。読み取り専用ファイルも削除する。

    パスが存在しない場合は何もしない。
    """
    await asyncio.to_thread(pytilpack.pathlib.rmtree, path, ignore_errors)


async def disk_usage(path: pathlib.Path | str) -> shutil._ntuple_diskusage:
    """ディスク使用量を非同期で取得する。"""
    return await asyncio.to_thread(shutil.disk_usage, path)


async def get_size(path: pathlib.Path | str) -> int:
    """ファイル・ディレクトリのサイズを非同期で取得する。"""
    return await asyncio.to_thread(pytilpack.pathlib.get_size, path)


async def delete_empty_dirs(path: str | pathlib.Path, keep_root: bool = True) -> None:
    """指定したパス以下の空ディレクトリを削除する。

    Args:
        path: 対象のパス
        keep_root: Trueの場合、指定したディレクトリ自体は削除しない
    """
    await asyncio.to_thread(pytilpack.pathlib.delete_empty_dirs, path, keep_root)


async def sync(src: str | pathlib.Path, dst: str | pathlib.Path, delete: bool = False) -> None:
    """コピー元からコピー先へ同期する。

    Args:
        src: コピー元のパス
        dst: コピー先のパス
        delete: Trueの場合、コピー元に存在しないファイル・ディレクトリをコピー先から削除する
    """
    await asyncio.to_thread(pytilpack.pathlib.sync, src, dst, delete)


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
    await asyncio.to_thread(pytilpack.pathlib.delete_old_files, path, before, delete_empty_dirs, keep_root_empty_dir)
