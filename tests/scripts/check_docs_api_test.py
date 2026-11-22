import importlib.util
import pathlib
import shutil

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "docs_api_checker", pathlib.Path(__file__).resolve().parents[2] / "scripts/check_docs_api.py"
)
assert _SPEC is not None and _SPEC.loader is not None
check_docs_api = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_docs_api)


@pytest.fixture(name="docs_root")
def _docs_root(tmp_path: pathlib.Path) -> pathlib.Path:
    source = pathlib.Path(__file__).resolve().parents[2]
    for name in ("pytilpack", "scripts", "docs"):
        shutil.copytree(source / name, tmp_path / name, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(source / "pyproject.toml", tmp_path / "pyproject.toml")
    return tmp_path


def test_current_documents(docs_root: pathlib.Path) -> None:
    assert not check_docs_api.check(docs_root)


@pytest.mark.parametrize(
    ("path", "old", "new", "location"),
    [
        ("docs/guide/index.md", "| `babel` | `pytilpack.babel`", "| `unknown` | `pytilpack.babel`", "extras一覧"),
        (
            "docs/guide/index.md",
            "コア依存: `beautifulsoup4`、",
            "コア依存: ",
            "コア依存",
        ),
        (
            "docs/guide/index.md",
            "| `babel` | `pytilpack.babel` |",
            "| `babel` | `pytilpack.quart` |",
            "extra babel 対象",
        ),
        (
            "docs/guide/index.md",
            "| `babel` | `pytilpack.babel` | `babel` |",
            "| `babel` | `pytilpack.babel` | `wrong-package` |",
            "extra babel 依存",
        ),
        ("docs/guide/cli.md", "## `pytilpack babel`", "## `pytilpack unknown`", "サブコマンド節"),
        ("docs/guide/index.md", "- `pytilpack.fastapi`", "- `pytilpack.unknown`", "モジュール一覧"),
    ],
)
def test_mismatch_is_rejected(docs_root: pathlib.Path, path: str, old: str, new: str, location: str) -> None:
    target = docs_root / path
    text = target.read_text(encoding="utf-8")
    assert text.count(old) == 1
    target.write_text(text.replace(old, new), encoding="utf-8")
    assert any(location in error for error in check_docs_api.check(docs_root))


def test_all_keeps_dependency_extras(docs_root: pathlib.Path) -> None:
    target = docs_root / "pyproject.toml"
    text = target.read_text(encoding="utf-8")
    target.write_text(text.replace('"sqlalchemy[asyncio]>=2.0"', '"sqlalchemy>=2.0"', 1), encoding="utf-8")
    assert any("pyproject.toml:all" in error for error in check_docs_api.check(docs_root))
