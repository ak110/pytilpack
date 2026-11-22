import pathlib
import sys
import uuid

import pytest

import pytilpack.importlib


@pytest.mark.parametrize("ignore_test", [True, False])
def test_import_all(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, ignore_test: bool) -> None:
    name = "fixture_" + uuid.uuid4().hex
    package = tmp_path / name
    (package / "nested").mkdir(parents=True)
    sources = {
        "__init__.py": 1,
        "nested/__init__.py": 2,
        "nested/ordinary.py": 3,
        "nested/ordinary_test.py": 4,
        "test_other.py": 5,
    }
    for path, value in sources.items():
        (package / path).write_text(f"VALUE = {value}\n", encoding="utf-8")
    expected = {name: 1, f"{name}.nested": 2, f"{name}.nested.ordinary": 3}
    if not ignore_test:
        expected.update({f"{name}.nested.ordinary_test": 4, f"{name}.test_other": 5})

    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        pytilpack.importlib.import_all(package, tmp_path, ignore_test=ignore_test)
        imported = {key: module for key, module in sys.modules.items() if key == name or key.startswith(name + ".")}
        assert imported.keys() == expected.keys()
        for key, value in expected.items():
            assert value == imported[key].VALUE
    finally:
        for key in tuple(sys.modules):
            if key == name or key.startswith(name + "."):
                sys.modules.pop(key)
