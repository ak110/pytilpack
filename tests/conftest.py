"""テストコード用の共通設定。"""

import pathlib

import babel.messages.mofile
import babel.messages.pofile
import pytest

TESTS_DIR = pathlib.Path(__file__).parent


def pytest_configure(config: pytest.Config) -> None:
    """pytest起動時に.poファイルから.moファイルをコンパイルする。"""
    del config  # noqa
    for po_path in sorted(TESTS_DIR.glob("**/*.po")):
        mo_path = po_path.with_suffix(".mo")
        # .poが更新されている場合のみ再コンパイル
        if mo_path.exists() and mo_path.stat().st_mtime >= po_path.stat().st_mtime:
            continue
        with po_path.open("rb") as f:
            catalog = babel.messages.pofile.read_po(f)
        with mo_path.open("wb") as f:
            babel.messages.mofile.write_mo(f, catalog)


@pytest.fixture
def data_dir():
    """テストデータのディレクトリパスを返す。"""
    yield TESTS_DIR / "data"
