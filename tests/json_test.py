import io
import json
import pathlib

import pytest

import pytilpack.json


def test_load_not_exist(tmp_path: pathlib.Path) -> None:
    # pylint: disable=use-implicit-booleaness-not-comparison
    assert pytilpack.json.load(tmp_path / "not_exist.json") == {}


def test_load_not_exist_strict(tmp_path: pathlib.Path) -> None:
    with pytest.raises(FileNotFoundError):
        pytilpack.json.load(tmp_path / "not_exist.json", strict=True)


_DATA = {"a": "💯", "c": 1}
_EXTERNAL_JSON = '{"a": "💯", "c": 1}'


def test_load_save(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "a.json"
    pytilpack.json.save(path, _DATA)
    saved = path.read_text(encoding="utf-8")
    assert json.loads(saved) == _DATA
    assert "💯" in saved

    path.write_bytes(_EXTERNAL_JSON.encode("utf-8"))
    assert pytilpack.json.load(path) == _DATA


def test_load_save_io() -> None:
    text = io.StringIO()
    binary = io.BytesIO()
    pytilpack.json.save(text, _DATA)
    pytilpack.json.save(binary, _DATA)
    for saved in (text.getvalue(), binary.getvalue().decode("utf-8")):
        assert json.loads(saved) == _DATA
        assert "💯" in saved

    assert pytilpack.json.load(io.StringIO(_EXTERNAL_JSON)) == _DATA
    assert pytilpack.json.load(io.BytesIO(_EXTERNAL_JSON.encode("utf-8"))) == _DATA


def test_edit_preserves_blank_lines() -> None:
    text = '{\n  "name": "old",\n\n  "count": 1\n}\n'
    result = pytilpack.json.edit(text, {("name",): "new"})
    assert result == '{\n  "name": "new",\n\n  "count": 1\n}\n'


def test_edit_file(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "a.json"
    p.write_text('{\n  "value": 1\n}\n', encoding="utf-8")
    pytilpack.json.edit_file(p, {("value",): 42})
    assert p.read_text(encoding="utf-8") == '{\n  "value": 42\n}\n'
