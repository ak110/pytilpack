"""テストコード。"""

import logging
import pathlib
import sys

import pytest

import pytilpack.importlib


def test_import_all(caplog: pytest.LogCaptureFixture) -> None:
    """import_all()のテスト。"""
    # ログレベルをDEBUGに設定してログをキャプチャ
    with caplog.at_level(logging.DEBUG):
        base_path = pathlib.Path(__file__).parent.parent
        pytilpack.importlib.import_all(base_path / "pytilpack", base_path)

    # モジュールがインポートされていることをログで確認
    log_messages = [record.message for record in caplog.records]
    assert any(message == "Importing module: pytilpack" for message in log_messages)
    assert any(message == "Importing module: pytilpack.importlib" for message in log_messages)


def test_import_all_ignore_test_false(tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture) -> None:
    """ignore_test=Falseのとき_test.py終わりのファイルがインポート対象になることを確認。

    修正前の演算子優先度バグでは ignore_test=False でも _test.py 終わりのファイルが
    常にスキップされていた。修正後は正しくインポート対象になることを検証する。
    """
    # 一時ディレクトリにダミーモジュールを作成
    pkg_dir = tmp_path / "mypkg_igntest"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "foo_test.py").write_text("VALUE = 42\n")

    # importlib.import_moduleが見つけられるようsys.pathに追加
    sys.path.insert(0, str(tmp_path))
    try:
        with caplog.at_level(logging.DEBUG):
            # ignore_test=False → _test.py 終わりのファイルもインポートされる
            pytilpack.importlib.import_all(pkg_dir, tmp_path, ignore_test=False)
    finally:
        sys.path.remove(str(tmp_path))

    log_messages = [record.message for record in caplog.records]
    assert any("mypkg_igntest.foo_test" in msg for msg in log_messages)


def test_import_all_ignore_test_true(tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture) -> None:
    """ignore_test=True（デフォルト）のとき_test.py終わりのファイルがスキップされることを確認。"""
    pkg_dir = tmp_path / "mypkg_igntrue"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "bar_test.py").write_text("VALUE = 99\n")
    (pkg_dir / "baz.py").write_text("VALUE = 0\n")

    sys.path.insert(0, str(tmp_path))
    try:
        with caplog.at_level(logging.DEBUG):
            pytilpack.importlib.import_all(pkg_dir, tmp_path, ignore_test=True)
    finally:
        sys.path.remove(str(tmp_path))

    log_messages = [record.message for record in caplog.records]
    # bar_test.py はスキップされる
    assert not any("mypkg_igntrue.bar_test" in msg for msg in log_messages)
    # baz.py はインポートされる
    assert any("mypkg_igntrue.baz" in msg for msg in log_messages)
