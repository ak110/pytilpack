import os
import pathlib
import tempfile

import babel.messages.mofile
import babel.messages.pofile
import pytest

import pytilpack.pytest

TESTS_DIR = pathlib.Path(__file__).parent


def pytest_configure(config: pytest.Config) -> None:
    del config  # noqa
    for po_path in sorted(TESTS_DIR.glob("**/*.po")):
        mo_path = po_path.with_suffix(".mo")
        if mo_path.exists() and mo_path.stat().st_mtime >= po_path.stat().st_mtime:
            continue
        with po_path.open("rb") as f:
            catalog = babel.messages.pofile.read_po(f)
        with tempfile.NamedTemporaryFile(dir=mo_path.parent, delete=False) as f:
            temporary_path = pathlib.Path(f.name)
        try:
            with temporary_path.open("wb") as f:
                babel.messages.mofile.write_mo(f, catalog)
            os.replace(temporary_path, mo_path)
        finally:
            temporary_path.unlink(missing_ok=True)


@pytest.fixture(autouse=True, scope="session")
def _pytilpack_basetmp(tmp_path_factory: pytest.TempPathFactory) -> None:  # type: ignore[misc]
    pytilpack.pytest.register_basetmp(tmp_path_factory)


@pytest.fixture
def data_dir():
    yield TESTS_DIR / "data"
