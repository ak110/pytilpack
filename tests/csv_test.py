import pathlib

import pytilpack.csv


def test_read_to_dict(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "test.csv"
    path.write_text("Alice,20\nBob,30")

    result = pytilpack.csv.read_to_dict(path, ["name", "age"])
    assert result == [{"name": "Alice", "age": "20"}, {"name": "Bob", "age": "30"}]


def test_read_to_dict_skipinitialspace(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "test.csv"
    path.write_text("Alice, 20\nBob, 30")

    result = pytilpack.csv.read_to_dict(path, ["name", "age"], skipinitialspace=True)
    assert result == [{"name": "Alice", "age": "20"}, {"name": "Bob", "age": "30"}]

    result_false = pytilpack.csv.read_to_dict(path, ["name", "age"], skipinitialspace=False)
    assert result_false == [{"name": "Alice", "age": " 20"}, {"name": "Bob", "age": " 30"}]


def test_read_to_dict_crlf(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "test.csv"
    path.write_bytes(b"Alice,20\r\nBob,30\r\n")

    result = pytilpack.csv.read_to_dict(path, ["name", "age"])
    assert result == [{"name": "Alice", "age": "20"}, {"name": "Bob", "age": "30"}]


def test_read_to_dict_encoding(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "test.csv"
    path.write_bytes("田中,20\n鈴木,30".encode("cp932"))

    result = pytilpack.csv.read_to_dict(path, ["name", "age"], encoding="cp932")
    assert result == [{"name": "田中", "age": "20"}, {"name": "鈴木", "age": "30"}]
