"""キャッシュモジュールのテスト。"""

from __future__ import annotations

import pathlib
import time
import typing

import pytest

from pytilpack import cache

CountingLoaderType = tuple[typing.Callable[[pathlib.Path], str], typing.Callable[[], int]]


@pytest.fixture(name="counting_loader")
def _counting_loader() -> CountingLoaderType:
    """呼び出し回数を記録するローダーとカウンタを返すフィクスチャ。"""
    call_count = 0

    def loader(path: pathlib.Path) -> str:
        nonlocal call_count
        call_count += 1
        return path.read_text()

    return loader, lambda: call_count


def test_cached_file_loader_errors() -> None:
    """CachedFileLoaderのエラーケースのテスト。"""
    # ローダー未指定
    loader = cache.CachedFileLoader[str]()
    with pytest.raises(ValueError, match="ローダー関数が指定されていません"):
        loader.load(pathlib.Path(__file__))

    # ファイルが存在しない
    loader = cache.CachedFileLoader(lambda p: p.read_text())
    with pytest.raises(FileNotFoundError):
        loader.load(pathlib.Path("not_exists"))


def test_cached_file_loader(
    tmp_path: pathlib.Path,
    counting_loader: CountingLoaderType,
) -> None:
    """CachedFileLoaderのキャッシュヒット・クリア・削除・無効化・オーバーライドのテスト。"""
    loader_func, get_count = counting_loader

    # キャッシュヒット: 2回目の読み込みはキャッシュを使用
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")

    loader = cache.CachedFileLoader(loader_func)
    assert loader.load(test_file) == "test"
    assert loader.load(test_file) == "test"
    assert get_count() == 1

    # キャッシュクリア: クリア後は再読み込み
    loader.clear()
    assert loader.load(test_file) == "test"
    assert get_count() == 2

    # 特定パスのキャッシュ削除
    test_file2 = tmp_path / "test2.txt"
    test_file2.write_text("test2")
    assert loader.load(test_file2) == "test2"
    assert get_count() == 3

    loader.remove(test_file)
    assert loader.load(test_file) == "test"  # 再読み込み
    assert loader.load(test_file2) == "test2"  # キャッシュ使用
    assert get_count() == 4

    # ファイル更新時のキャッシュ無効化
    time.sleep(0.1)  # ファイルのタイムスタンプ更新のための待機
    test_file.write_text("updated")
    assert loader.load(test_file) == "updated"

    # ローダーオーバーライド
    loader_upper = cache.CachedFileLoader(lambda p: p.read_text().upper())
    assert loader_upper.load(test_file) == "UPDATED"
    assert loader_upper.load(test_file, lambda p: p.read_text().lower()) == "updated"
