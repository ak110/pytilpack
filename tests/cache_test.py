from __future__ import annotations

import os
import pathlib
import typing

import pytest

from pytilpack import cache

CountingLoaderType = tuple[typing.Callable[[pathlib.Path], str], typing.Callable[[], int]]


@pytest.fixture(name="counting_loader")
def _counting_loader() -> CountingLoaderType:
    call_count = 0

    def loader(path: pathlib.Path) -> str:
        nonlocal call_count
        call_count += 1
        return path.read_text()

    return loader, lambda: call_count


def test_cached_file_loader_errors() -> None:
    loader = cache.CachedFileLoader[str]()
    with pytest.raises(ValueError, match="ローダー関数が指定されていません"):
        loader.load(pathlib.Path(__file__))

    loader = cache.CachedFileLoader(lambda p: p.read_text())
    with pytest.raises(FileNotFoundError):
        loader.load(pathlib.Path("not_exists"))


def test_cached_file_loader(
    tmp_path: pathlib.Path,
    counting_loader: CountingLoaderType,
) -> None:
    loader_func, get_count = counting_loader

    test_file = tmp_path / "test.txt"
    test_file.write_text("test")

    loader = cache.CachedFileLoader(loader_func)
    assert loader.load(test_file) == "test"
    assert loader.load(test_file) == "test"
    assert get_count() == 1

    loader.clear()
    assert loader.load(test_file) == "test"
    assert get_count() == 2

    test_file2 = tmp_path / "test2.txt"
    test_file2.write_text("test2")
    assert loader.load(test_file2) == "test2"
    assert get_count() == 3

    loader.remove(test_file)
    assert loader.load(test_file) == "test"
    assert loader.load(test_file2) == "test2"
    assert get_count() == 4

    previous_stat = test_file.stat()
    test_file.write_text("updated")
    os.utime(test_file, ns=(previous_stat.st_atime_ns, previous_stat.st_mtime_ns + 2_000_000_000))
    assert loader.load(test_file) == "updated"

    loader_upper = cache.CachedFileLoader(lambda p: p.read_text().upper())
    assert loader_upper.load(test_file) == "UPDATED"
    assert loader_upper.load(test_file, lambda p: p.read_text().lower()) == "updated"


def test_cached_file_loader_error_messages() -> None:
    with pytest.raises(ValueError, match="load\\(\\)のloader引数か、CachedFileLoader\\(\\)のloader引数で指定する"):
        cache.CachedFileLoader[str]().load(pathlib.Path(__file__))
    with pytest.raises(FileNotFoundError, match="パスの指定を見直すか、ファイルを作成してから呼び出す"):
        cache.CachedFileLoader(lambda p: p.read_text()).load(pathlib.Path("not_exists"))
