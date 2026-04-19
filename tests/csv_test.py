"""テストコード。"""

import pathlib

import pytilpack.csv


def test_read_to_dict(tmp_path: pathlib.Path) -> None:
    """read_to_dict()のテスト。"""
    # fieldnamesを指定するため、ヘッダー行なしのCSVを使う
    path = tmp_path / "test.csv"
    path.write_text("Alice,20\nBob,30")

    result = pytilpack.csv.read_to_dict(path, ["name", "age"])
    assert result == [{"name": "Alice", "age": "20"}, {"name": "Bob", "age": "30"}]


def test_read_to_dict_fieldnames(tmp_path: pathlib.Path) -> None:
    """fieldnamesが実際に効くことを確認するテスト。"""
    # ヘッダー行なしで列名を指定する
    path = tmp_path / "test.csv"
    path.write_text("Alice,20\nBob,30")

    result = pytilpack.csv.read_to_dict(path, ["name", "age"])
    assert result == [{"name": "Alice", "age": "20"}, {"name": "Bob", "age": "30"}]


def test_read_to_dict_skipinitialspace(tmp_path: pathlib.Path) -> None:
    """skipinitialspaceが実際に効くことを確認するテスト。"""
    # 各値の先頭にスペースを入れたCSV
    path = tmp_path / "test.csv"
    path.write_text("Alice, 20\nBob, 30")

    # skipinitialspace=True（既定）: 先頭スペースが除去される
    result = pytilpack.csv.read_to_dict(path, ["name", "age"], skipinitialspace=True)
    assert result == [{"name": "Alice", "age": "20"}, {"name": "Bob", "age": "30"}]

    # skipinitialspace=False: 先頭スペースが残る
    result_false = pytilpack.csv.read_to_dict(path, ["name", "age"], skipinitialspace=False)
    assert result_false == [{"name": "Alice", "age": " 20"}, {"name": "Bob", "age": " 30"}]


def test_read_to_dict_lineterminator(tmp_path: pathlib.Path) -> None:
    """lineterminatorが実際に効くことを確認するテスト。"""
    # \r\n改行のCSV
    path = tmp_path / "test.csv"
    path.write_bytes(b"Alice,20\r\nBob,30\r\n")

    result = pytilpack.csv.read_to_dict(path, ["name", "age"], lineterminator="\r\n")
    assert result == [{"name": "Alice", "age": "20"}, {"name": "Bob", "age": "30"}]


def test_read_to_dict_encoding(tmp_path: pathlib.Path) -> None:
    """encodingが実際に効くことを確認するテスト。"""
    path = tmp_path / "test.csv"
    # CP932エンコーディングで日本語を含むCSVを書き込む
    path.write_bytes("田中,20\n鈴木,30".encode("cp932"))

    result = pytilpack.csv.read_to_dict(path, ["name", "age"], encoding="cp932")
    assert result == [{"name": "田中", "age": "20"}, {"name": "鈴木", "age": "30"}]
