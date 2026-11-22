__lazy_modules__ = [
    "asyncio",
    "datetime",
    "logging",
    "pathlib",
    "pytilpack.io",
    "pytilpack.json",
    "pytilpack.jsonc",
    "pytilpack.pathlib",
    "shutil",
    "typing",
]

import asyncio
import datetime as dt
import logging
import pathlib
import shutil
import typing

import pytilpack.io
import pytilpack.json
import pytilpack.jsonc
import pytilpack.pathlib

logger = logging.getLogger(__name__)

__all__ = [
    "read_json",
    "write_json",
    "read_jsonc",
    "read_yaml",
    "read_yaml_all",
    "write_yaml",
    "write_yaml_all",
    "read_text",
    "write_text",
    "append_text",
    "read_bytes",
    "write_bytes",
    "append_bytes",
    "copy2",
    "copytree",
    "move",
    "delete_file",
    "rmtree",
    "disk_usage",
    "get_size",
    "delete_empty_dirs",
    "sync",
    "delete_old_files",
]


async def read_json(
    path: pytilpack.io.PathOrIO,
    encoding: str = "utf-8",
    errors: str = "replace",
    strict: bool = False,
    **kwargs,
) -> typing.Any:
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
    import pytilpack.yaml  # pylint: disable=import-outside-toplevel,redefined-outer-name

    # arid: disable
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
    # arid: enable


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
    import pytilpack.yaml  # pylint: disable=import-outside-toplevel,redefined-outer-name

    # arid: disable
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
    # arid: enable


async def read_text(path: pathlib.Path | str, encoding: str = "utf-8", errors: str = "strict") -> str:
    path = pathlib.Path(path)
    return await asyncio.to_thread(path.read_text, encoding, errors)


async def write_text(path: pathlib.Path | str, data: str, encoding: str = "utf-8", errors: str = "strict") -> None:
    path = pathlib.Path(path)
    await asyncio.to_thread(path.write_text, data, encoding, errors)


async def append_text(path: pathlib.Path | str, data: str, encoding: str = "utf-8", errors: str = "strict") -> None:
    await asyncio.to_thread(pytilpack.pathlib.append_text, path, data, encoding, errors)


async def read_bytes(path: pathlib.Path | str) -> bytes:
    path = pathlib.Path(path)
    return await asyncio.to_thread(path.read_bytes)


async def write_bytes(path: pathlib.Path | str, data: bytes) -> None:
    path = pathlib.Path(path)
    await asyncio.to_thread(path.write_bytes, data)


async def append_bytes(path: pathlib.Path | str, data: bytes) -> None:
    await asyncio.to_thread(pytilpack.pathlib.append_bytes, path, data)


async def copy2(src: pathlib.Path | str, dst: pathlib.Path | str) -> None:
    await asyncio.to_thread(shutil.copy2, src, dst)


async def copytree(
    src: pathlib.Path | str,
    dst: pathlib.Path | str,
    dirs_exist_ok: bool = False,
) -> None:
    await asyncio.to_thread(shutil.copytree, src, dst, dirs_exist_ok=dirs_exist_ok)


async def move(src: pathlib.Path | str, dst: pathlib.Path | str) -> None:
    await asyncio.to_thread(shutil.move, src, dst)


async def delete_file(path: pathlib.Path | str) -> None:
    path = pathlib.Path(path)
    await asyncio.to_thread(pytilpack.pathlib.delete_file, path)


async def rmtree(path: pathlib.Path | str, ignore_errors: bool = False) -> "pytilpack.pathlib.RmtreeResult":
    return await asyncio.to_thread(pytilpack.pathlib.rmtree, path, ignore_errors)


async def disk_usage(path: pathlib.Path | str) -> shutil._ntuple_diskusage:
    return await asyncio.to_thread(shutil.disk_usage, path)


async def get_size(path: pathlib.Path | str) -> int:
    return await asyncio.to_thread(pytilpack.pathlib.get_size, path)


async def delete_empty_dirs(path: str | pathlib.Path, keep_root: bool = True) -> None:
    await asyncio.to_thread(pytilpack.pathlib.delete_empty_dirs, path, keep_root)


async def sync(src: str | pathlib.Path, dst: str | pathlib.Path, delete: bool = False) -> None:
    await asyncio.to_thread(pytilpack.pathlib.sync, src, dst, delete)


async def delete_old_files(
    path: str | pathlib.Path,
    before: dt.datetime,
    delete_empty_dirs: bool = True,  # pylint: disable=redefined-outer-name
    keep_root_empty_dir: bool = True,
) -> None:
    await asyncio.to_thread(pytilpack.pathlib.delete_old_files, path, before, delete_empty_dirs, keep_root_empty_dir)
