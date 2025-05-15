"""キャッシュモジュールのテスト。"""

from __future__ import annotations

import pathlib
import time

import pytest

from pytilpack import cache


def test_loader_none() -> None:
    """ローダーが未指定の場合のテスト。"""
    loader = cache.CachedFileLoader[str]()
    with pytest.raises(ValueError, match="ローダー関数が指定されていません"):
        loader.load(pathlib.Path(__file__))


def test_file_not_found() -> None:
    """ファイルが存在しない場合のテスト。"""
    loader = cache.CachedFileLoader(lambda p: p.read_text())
    with pytest.raises(FileNotFoundError):
        loader.load(pathlib.Path("not_exists"))


def test_cache_hit(tmp_path: pathlib.Path) -> None:
    """キャッシュヒットのテスト。"""
    # テストファイルの準備
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")

    # 呼び出し回数を数えるローダーの準備
    call_count = 0

    def counting_loader(path: pathlib.Path) -> str:
        nonlocal call_count
        call_count += 1
        return path.read_text()

    # キャッシュヒットのテスト
    loader = cache.CachedFileLoader(counting_loader)
    assert loader.load(test_file) == "test"
    assert loader.load(test_file) == "test"
    assert call_count == 1  # 2回目の読み込みはキャッシュを使用


def test_cache_invalidation(tmp_path: pathlib.Path) -> None:
    """ファイル更新時のキャッシュ無効化テスト。"""
    # テストファイルの準備
    test_file = tmp_path / "test.txt"
    test_file.write_text("old")

    # 初期コンテンツの読み込み
    loader = cache.CachedFileLoader(lambda p: p.read_text())
    assert loader.load(test_file) == "old"

    # タイムスタンプ更新のため少し待機
    time.sleep(0.1)  # ファイルのタイムスタンプ更新のための待機
    test_file.write_text("new")

    # 新しいコンテンツが読み込まれることを確認
    assert loader.load(test_file) == "new"


def test_clear_cache(tmp_path: pathlib.Path) -> None:
    """キャッシュクリアのテスト。"""
    # テストファイルの準備
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")

    # 呼び出し回数を数えるローダーの準備
    call_count = 0

    def counting_loader(path: pathlib.Path) -> str:
        nonlocal call_count
        call_count += 1
        return path.read_text()

    # キャッシュの動作確認
    loader = cache.CachedFileLoader(counting_loader)
    assert loader.load(test_file) == "test"
    assert loader.load(test_file) == "test"
    assert call_count == 1

    # キャッシュクリア後の再読み込み確認
    loader.clear()
    assert loader.load(test_file) == "test"
    assert call_count == 2


def test_remove_cache(tmp_path: pathlib.Path) -> None:
    """特定パスのキャッシュ削除テスト。"""
    # テストファイルの準備
    test_file1 = tmp_path / "test1.txt"
    test_file2 = tmp_path / "test2.txt"
    test_file1.write_text("test1")
    test_file2.write_text("test2")

    # 呼び出し回数を数えるローダーの準備
    call_count = 0

    def counting_loader(path: pathlib.Path) -> str:
        nonlocal call_count
        call_count += 1
        return path.read_text()

    # ファイルの読み込み
    loader = cache.CachedFileLoader(counting_loader)
    assert loader.load(test_file1) == "test1"
    assert loader.load(test_file2) == "test2"
    assert call_count == 2

    # test_file1のキャッシュを削除
    loader.remove(test_file1)

    # test_file1は再読み込み、test_file2はキャッシュを使用
    assert loader.load(test_file1) == "test1"
    assert loader.load(test_file2) == "test2"
    assert call_count == 3


def test_override_loader(tmp_path: pathlib.Path) -> None:
    """ローダー関数オーバーライドのテスト。"""
    # テストファイルの準備
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")

    # デフォルトで大文字変換するローダーを設定
    loader = cache.CachedFileLoader(lambda p: p.read_text().upper())
    assert loader.load(test_file) == "TEST"

    # 小文字変換するローダーでオーバーライド
    assert loader.load(test_file, lambda p: p.read_text().lower()) == "test"
