import importlib.util
import pathlib
import shutil

import pytest

_SOURCE = pathlib.Path(__file__).resolve().parents[2]

_SPEC = importlib.util.spec_from_file_location("docs_api_checker", _SOURCE / "scripts/check_docs_api.py")
assert _SPEC is not None and _SPEC.loader is not None
check_docs_api = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_docs_api)


@pytest.fixture(name="docs_root")
def _docs_root(tmp_path: pathlib.Path) -> pathlib.Path:
    for name in (
        "pyproject.toml",
        "docs/guide/index.md",
        "docs/guide/cli.md",
        "scripts/check_extras_imports.py",
        "pytilpack/cli/main.py",
    ):
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_SOURCE / name, dest)
    for module in (_SOURCE / "pytilpack").iterdir():
        entry = module / "__init__.py" if module.is_dir() else module
        if entry.suffix == ".py" and entry.is_file():
            dest = tmp_path / entry.relative_to(_SOURCE)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                dest.touch()
    return tmp_path


def test_current_documents() -> None:
    assert not check_docs_api.check(_SOURCE)


@pytest.mark.parametrize(
    ("path", "old", "new", "location", "missing", "excess"),
    [
        (
            "docs/guide/index.md",
            "| `babel` | `pytilpack.babel`",
            "| `unknown` | `pytilpack.babel`",
            "extras一覧",
            "babel",
            "unknown",
        ),
        (
            "docs/guide/index.md",
            "コア依存: `beautifulsoup4`、",
            "コア依存: ",
            "コア依存",
            "beautifulsoup4",
            "",
        ),
        (
            "docs/guide/index.md",
            "| `babel` | `pytilpack.babel` |",
            "| `babel` | `pytilpack.quart` |",
            "extra babel 対象",
            "babel",
            "quart",
        ),
        (
            "docs/guide/index.md",
            "| `babel` | `pytilpack.babel` | `babel` |",
            "| `babel` | `pytilpack.babel` | `wrong-package` |",
            "extra babel 依存",
            "babel",
            "wrong-package",
        ),
        ("docs/guide/cli.md", "## `pytilpack babel`", "## `pytilpack unknown`", "サブコマンド節", "babel", "unknown"),
        ("docs/guide/index.md", "- `pytilpack.fastapi`", "- `pytilpack.unknown`", "モジュール一覧", "fastapi", "unknown"),
    ],
)
def test_mismatch_is_rejected(
    docs_root: pathlib.Path, path: str, old: str, new: str, location: str, missing: str, excess: str
) -> None:
    target = docs_root / path
    text = target.read_text(encoding="utf-8")
    assert text.count(old) == 1
    target.write_text(text.replace(old, new), encoding="utf-8")
    errors = [error for error in check_docs_api.check(docs_root) if f":{location}:" in error]
    assert len(errors) == 1
    assert f"不足={[missing] if missing else []}" in errors[0]
    assert f"過剰={[excess] if excess else []}" in errors[0]


def test_all_keeps_dependency_extras(docs_root: pathlib.Path) -> None:
    target = docs_root / "pyproject.toml"
    text = target.read_text(encoding="utf-8")
    before, dependency, after = text.partition('"sqlalchemy[asyncio]>=2.0"')
    assert dependency
    target.write_text(before + '"sqlalchemy>=2.0"' + after, encoding="utf-8")
    errors = [error for error in check_docs_api.check(docs_root) if error.startswith("pyproject.toml:all:")]
    assert len(errors) == 1
    assert "不足=['sqlalchemy[asyncio]']" in errors[0]
    assert "過剰=['sqlalchemy']" in errors[0]
