"""テストコード。"""

import io
import pathlib

import pytilpack.yaml


def test_load_not_exist(tmp_path: pathlib.Path) -> None:
    assert pytilpack.yaml.load(tmp_path / "not_exist.yaml") == {}


def test_load_save(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "a.yaml"
    data = {"c": "💯\nあいうえお\n\n", "a": 1}

    pytilpack.yaml.save(path, data)
    data2 = pytilpack.yaml.load(path)

    assert data["a"] == data2["a"]
    assert data["c"] == data2["c"]
    assert tuple(sorted(data)) == tuple(sorted(data2))

    s = pathlib.Path(path).read_text("utf-8")
    assert s == "c: |+\n  💯\n  あいうえお\n\na: 1\n"


def test_load_all_not_exist(tmp_path: pathlib.Path) -> None:
    # pylint: disable=use-implicit-booleaness-not-comparison
    assert pytilpack.yaml.load_all(tmp_path / "not_exist.yaml") == []


def test_load_all_save_all(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "a.yaml"
    data = [{"key": "value1", "num": 1}, {"key": "value2", "num": 2}]

    pytilpack.yaml.save_all(path, data)
    data2 = pytilpack.yaml.load_all(path)

    assert len(data2) == 2
    assert data[0] == data2[0]
    assert data[1] == data2[1]


def test_load_save_io() -> None:
    """IO[str] / IO[bytes] での load/save のテスト。"""
    data = {"key": "💯", "num": 1}

    # StringIO で save → load
    buf = io.StringIO()
    pytilpack.yaml.save(buf, data)
    buf.seek(0)
    data2 = pytilpack.yaml.load(buf)
    assert data == data2

    # BytesIO で save → load
    buf_b = io.BytesIO()
    pytilpack.yaml.save(buf_b, data)
    buf_b.seek(0)
    data3 = pytilpack.yaml.load(buf_b)
    assert data == data3


def test_block_scalar() -> None:
    """ブロックスカラーのテスト。"""
    # 改行を含む文字列はブロックスカラー (|) で出力される
    assert pytilpack.yaml.dumps({"key": "line1\nline2\n"}) == "key: |\n  line1\n  line2\n"
    # タブ、末尾スペース、\r\n、ヌル文字などがあればブロックスカラーにならない
    assert pytilpack.yaml.dumps({"key": "line1\ttab\nline2\n"}) == 'key: "line1\\ttab\\nline2\\n"\n'
    assert pytilpack.yaml.dumps({"key": "line1 \nline2\n"}) == 'key: "line1 \\nline2\\n"\n'
    assert pytilpack.yaml.dumps({"key": "line1\r\nline2\n"}) == 'key: "line1\\r\\nline2\\n"\n'
    assert pytilpack.yaml.dumps({"key": "line1\nline2\0null\n"}) == 'key: "line1\\nline2\\0null\\n"\n'
    # 末尾のみ改行は通常の形式で出力される
    assert pytilpack.yaml.dumps({"key": "only at end\n"}) == "key: 'only at end\n\n  '\n"
    # 改行を含まない文字列は通常の形式で出力される
    assert pytilpack.yaml.dumps({"key": "no newline"}) == "key: no newline\n"


def test_load_all_save_all_io() -> None:
    """IO[str] / IO[bytes] での load_all/save_all のテスト。"""
    data = [{"key": "value1"}, {"key": "value2"}]

    # StringIO で save_all → load_all
    buf = io.StringIO()
    pytilpack.yaml.save_all(buf, data)
    buf.seek(0)
    data2 = pytilpack.yaml.load_all(buf)
    assert data == data2

    # BytesIO で save_all → load_all
    buf_b = io.BytesIO()
    pytilpack.yaml.save_all(buf_b, data)
    buf_b.seek(0)
    data3 = pytilpack.yaml.load_all(buf_b)
    assert data == data3
